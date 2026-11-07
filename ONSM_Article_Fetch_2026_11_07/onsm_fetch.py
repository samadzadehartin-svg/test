#!/usr/bin/env python3
"""ONSM lawful open-access full-text harvester. Input: records.json. Output: two DOCX + audit CSV.
Sources: Europe PMC/PMC OA XML, Unpaywall (email required), OpenAlex OA locations.
No paywall evasion or unauthorized mirrors. Per-PMID checkpoint files enable resuming.
"""
import argparse, csv, json, os, re, sys, time, random, pathlib, hashlib, logging
from urllib.parse import quote, urlparse
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, Inches
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

AGENT='ONSM-Literature-Research/1.0 (academic research; open access only)'
BASE='https://www.ebi.ac.uk/europepmc/webservices/rest/'
LOG=logging.getLogger('onsm')

def client():
    s=requests.Session();s.headers.update({'User-Agent':AGENT,'Accept':'application/json, application/xml, text/html, application/pdf;q=0.8, */*;q=0.5'})
    retry=Retry(total=3,backoff_factor=1.3,status_forcelist=[429,500,502,503,504],allowed_methods=['GET'],respect_retry_after_header=True)
    s.mount('https://',HTTPAdapter(max_retries=retry,pool_connections=8,pool_maxsize=8));return s

def get(s,url,params=None,timeout=28):
    try:
        r=s.get(url,params=params,timeout=timeout,allow_redirects=True)
        if r.status_code==200 and len(r.content)<30_000_000:return r
        LOG.debug('HTTP %s at %s',r.status_code,url)
    except Exception as e:LOG.debug('%s: %s',url,str(e)[:150])
    return None

def plain(xml):
    soup=BeautifulSoup(xml,'xml')
    for item in soup.select('ref-list, ack, author-notes, permissions, license, back, supplementary-material, fig, table-wrap, xref, inline-formula'):
        item.decompose()
    article=soup.find('article') or soup
    blocks=[]
    title=article.find('article-title')
    if title:blocks.append(title.get_text(' ',strip=True))
    body=article.find('body')
    if not body:return ''
    for tag in body.find_all(['title','p','list-item'],recursive=True):
        if tag.name=='p' and tag.find_parent('list-item'):continue
        t=tag.get_text(' ',strip=True)
        if len(t)>3 and (not blocks or t!=blocks[-1]):blocks.append(t)
    return '\n\n'.join(blocks)

def pdf_extract(content):
    if not content.startswith(b'%PDF-'):return ''
    try:
        import fitz
        doc=fitz.open(stream=content,filetype='pdf')
        if len(doc)<1 or len(doc)>150:return ''
        return '\n\n'.join(page.get_text('text') for page in doc).strip()
    except Exception as e:LOG.debug('PDF error: %s',e);return ''

def html_extract(content):
    try:
        import trafilatura
        t=trafilatura.extract(content,include_comments=False,include_tables=True,favor_recall=True)
        return t or ''
    except Exception:return ''

def valid(t):
    # Avoid confusing an abstract/landing page with the full article
    return bool(t and len(t)>1800 and len(re.findall(r'\b\w+\b',t))>300)

def from_url(s,url):
    if not url or not url.lower().startswith('https://'):return ''
    host=(urlparse(url).hostname or '').lower()
    if host in ('localhost','127.0.0.1') or host.endswith('.local'):return ''
    r=get(s,url,timeout=40)
    if not r:return ''
    ct=r.headers.get('Content-Type','').lower()
    if r.content.startswith(b'%PDF-') or 'application/pdf' in ct:return pdf_extract(r.content)
    if 'xml' in ct or r.content[:150].lstrip().startswith(b'<?xml'):return plain(r.content)
    if 'html' in ct:return html_extract(r.content)
    return ''

def european(s,pmid):
    r=get(s,BASE+'search',{'query':'EXT_ID:'+str(pmid)+' AND SRC:MED','format':'json','pageSize':1})
    if not r:return [],{}
    try:d=r.json()['resultList']['result'][0]
    except Exception:return [],{}
    pmcid=d.get('pmcid',''); candidates=[]
    if pmcid:
        candidates.append(('Europe PMC fullTextXML',BASE+pmcid+'/fullTextXML'))
        # XML not always available for PMCID, OA API may provide other rights-cleared formats
    return candidates,{'pmcid':pmcid,'isOpenAccess':d.get('isOpenAccess',''),'abstractText':d.get('abstractText','')}

def openalex(s,doi,pmid):
    if doi:
        url='https://api.openalex.org/works/https://doi.org/'+quote(doi,safe='/')
    elif pmid:url='https://api.openalex.org/works/https://pubmed.ncbi.nlm.nih.gov/'+quote(str(pmid))
    else:return []
    r=get(s,url)
    if not r:return []
    try:d=r.json()
    except Exception:return []
    if not d.get('is_oa'):return []
    locs=[d.get('best_oa_location')]+(d.get('locations') or [])
    out=[]
    for loc in locs:
        if isinstance(loc,dict) and loc.get('is_oa'):
            for field in ('pdf_url','landing_page_url'):
                u=loc.get(field)
                if u and u.startswith('https://'):out.append(('OpenAlex OA '+field,u))
    return out

def unpaywall(s,doi,email):
    if not email or not doi or '@' not in email:return []
    r=get(s,'https://api.unpaywall.org/v2/'+quote(doi,safe='/'),{'email':email})
    if not r:return []
    try:d=r.json()
    except Exception:return []
    if not d.get('is_oa'):return []
    out=[]
    for loc in [d.get('best_oa_location')]+(d.get('oa_locations') or []):
        if isinstance(loc,dict):
            for name in ('url_for_pdf','url_for_landing_page'):
                if loc.get(name):out.append(('Unpaywall OA '+name,loc[name]))
    return out

def find_fulltext(s,row,email):
    pmid=str(row.get('pmid') or '');doi=str(row.get('doi') or '').strip()
    candidates,meta=european(s,pmid)
    if meta.get('isOpenAccess')!='Y':
        # Europe PMC fullTextXML can still be available under reuse terms; attempt checks anyway.
        pass
    try:candidates+=unpaywall(s,doi,email)
    except Exception as e:LOG.warning('Unpaywall %s %s',pmid,e)
    try:candidates+=openalex(s,doi,pmid)
    except Exception as e:LOG.warning('OpenAlex %s %s',pmid,e)
    seen=set()
    for source,url in candidates:
        if url in seen:continue
        seen.add(url)
        try:
            if source=='Europe PMC fullTextXML':
                r=get(s,url)
                result=plain(r.content) if r else ''
            else:result=from_url(s,url)
            if valid(result):return result,source,url,meta
        except Exception as e:LOG.warning('Candidate failed %s %s: %s',pmid,url,str(e)[:130])
        time.sleep(0.2)
    return '', '', '',meta

def key(row):return re.sub('[^0-9A-Za-z_.-]','_',str(row.get('pmid') or row.get('doi') or row.get('title')))

def set_doc_style(doc):
    sec=doc.sections[0];sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.7)
    sec.left_margin=Inches(.72);sec.right_margin=Inches(.72)
    doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(9)

def add_meta(doc,r):
    for label,v in [('Authors','; '.join(r.get('authors') or [])),('Journal date',r.get('pubdate') or r.get('year')),
                    ('PMID',r.get('pmid')),('DOI',r.get('doi')),('Category',r.get('category'))]:
        doc.add_paragraph(f'{label}: {v or "Not provided"}')

def paragraphs(doc,text):
    # Long articles use moderate chunks to keep Word responsive
    for p in re.split(r'\n\s*\n',text or ''):
        p=' '.join(p.split())
        if not p:continue
        while len(p)>8000:
            pos=p.rfind(' ',0,7000)
            if pos<1000:pos=7000
            doc.add_paragraph(p[:pos]);p=p[pos:].lstrip()
        doc.add_paragraph(p)

def output(records,checkpoint,outdir):
    all_doc=Document();miss=Document();set_doc_style(all_doc);set_doc_style(miss)
    all_doc.add_heading('ONSM Article Texts — Available Open Access and Abstract Fallbacks',0)
    miss.add_heading('ONSM Articles Without Retrieved Full Text',0)
    all_doc.add_paragraph('Contains full text only when retrieved from an accessible open-access source. All other records contain the supplied abstract. Duplicate input records are retained. The source URL and retrieval status are shown per record.')
    miss.add_paragraph('Entries listed once per unique article. These could be paywalled, unavailable in an indexed repository, or temporarily unreachable; this file does not prove an article is paywalled.')
    missing_keys=set();status=[]
    for i,row in enumerate(records,1):
        k=key(row);f=checkpoint/(k+'.json')
        try:result=json.loads(f.read_text(encoding='utf8')) if f.exists() else {}
        except Exception:result={}
        full=result.get('status')=='full_text' and bool(result.get('text'))
        all_doc.add_heading(f'{i}. {row.get("title") or "Untitled"}',level=2)
        add_meta(all_doc,row)
        all_doc.add_paragraph('RETRIEVAL: '+('FULL TEXT' if full else 'ABSTRACT ONLY / FULL TEXT NOT RETRIEVED'))
        if full:
            all_doc.add_paragraph('Source: '+str(result.get('source'))+' | '+str(result.get('url')))
            paragraphs(all_doc,result['text'])
        else:
            paragraphs(all_doc,row.get('abstract') or result.get('abstract') or '[No abstract present in supplied files]')
            if k not in missing_keys:
                missing_keys.add(k)
                miss.add_heading(f'{len(missing_keys)}. {row.get("title") or "Untitled"}',level=2)
                add_meta(miss,row)
                miss.add_paragraph('PubMed: https://pubmed.ncbi.nlm.nih.gov/'+str(row.get('pmid') or ''))
                miss.add_paragraph('Status: '+str(result.get('status') or 'not_attempted'))
        status.append({'input_index':i,'pmid':row.get('pmid'),'doi':row.get('doi'),'status':'full_text' if full else 'abstract_only','source':result.get('source',''),'url':result.get('url',''),'error':result.get('error','')})
    main=outdir/'ONSM_All_Articles_FullText_or_Abstract.docx';missing=outdir/'ONSM_Missing_FullText_DOI_List.docx'
    all_doc.save(main);miss.save(missing)
    with (outdir/'ONSM_Retrieval_Audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(status[0]) if status else ['pmid']);w.writeheader();w.writerows(status)
    return main,missing,len(missing_keys)

def run(args):
    input_path=pathlib.Path(args.input);outdir=pathlib.Path(args.output);outdir.mkdir(parents=True,exist_ok=True)
    checkpoint=outdir/'checkpoint';checkpoint.mkdir(exist_ok=True)
    rows=json.loads(input_path.read_text(encoding='utf-8'))
    unique={}
    for r in rows:unique.setdefault(key(r),r)
    s=client();stats={'full_text':0,'abstract_only':0,'error':0,'cached':0}
    for n,(k,row) in enumerate(unique.items(),1):
        f=checkpoint/(k+'.json')
        if f.exists() and not args.retry_missing:
            stats['cached']+=1;continue
        if f.exists() and args.retry_missing:
            try:
                old=json.loads(f.read_text(encoding='utf8'))
                if old.get('status')=='full_text':stats['cached']+=1;continue
            except Exception:pass
        item={'status':'abstract_only','text':'','source':'','url':'','pmid':row.get('pmid'),'doi':row.get('doi'),'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        try:
            text,source,url,meta=find_fulltext(s,row,args.email)
            if text:item.update(status='full_text',text=text,source=source,url=url)
            elif meta.get('abstractText'):item['abstract']=meta['abstractText']
        except KeyboardInterrupt:raise
        except Exception as e:item.update(status='error',error=str(e)[:500]);LOG.exception('Article failed: %s',k)
        tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(item,ensure_ascii=False),encoding='utf-8');tmp.replace(f)
        stats[item['status']]+=1
        print(f'[{n}/{len(unique)}] PMID {row.get("pmid")}: {item["status"]} ({source if item["status"]=="full_text" else "no OA full text"})',flush=True)
        time.sleep(args.delay)
    main,missing,total=output(rows,checkpoint,outdir)
    print('\nDONE:')
    print(main);print(missing);print('Unique without full text:',total)
    print('Stats:',stats)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='records.json');ap.add_argument('--output',default='ONSM_Results');ap.add_argument('--email',default=os.environ.get('UNPAYWALL_EMAIL',''));ap.add_argument('--delay',type=float,default=0.35);ap.add_argument('--retry-missing',action='store_true');ap.add_argument('--offline-test',action='store_true');args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    if args.offline_test:
        args.output='ONSM_Test_Results';args.delay=0
        rows=json.loads(pathlib.Path(args.input).read_text());p=pathlib.Path(args.output);p.mkdir(exist_ok=True);(p/'checkpoint').mkdir(exist_ok=True)
        a,b,c=output(rows[:5],p/'checkpoint',p);print('Offline test generated:',a,b,c)
    else:run(args)