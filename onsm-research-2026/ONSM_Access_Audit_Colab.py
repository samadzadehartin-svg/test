#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONSM full-record audit. Usage: python ONSM_Access_Audit_Colab.py
All 536 input occurrences are retained, including repeated PMIDs.
Online metadata + availability: Europe PMC and PubMed/NCBI.
Public PMC XML is optionally included; paywalled full texts are never circumvented.
"""
import base64
import collections
import csv
import gzip
import json
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', '-q', 'install', 'requests', 'python-docx'])
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

INPUT = Path('ONSM_ALL_536_with_duplicates.html')
OUTPUT_DOCX = Path('ONSM_536_Full_Article_Access_Audit.docx')
OUTPUT_CSV = Path('ONSM_536_Access_Audit.csv')
CACHE_FILE = Path('ONSM_access_audit_cache.json')
TEXT_CACHE = Path('ONSM_public_fulltext_cache')
# This does not restrict the number of records. It only limits requests per batch.
BATCH_SIZE = 18
FETCH_PUBLIC_FULL_TEXT = True
# Every occurrence remains in the Word. Duplicate full texts are repeated too.
REPEAT_TEXT_FOR_DUPLICATES = True
TIMEOUT = (15, 60)
CONTACT_EMAIL = os.getenv('NCBI_EMAIL', '')  # optional for policy-compliant identification


def load_input(path):
    s = path.read_text(encoding='utf-8')
    m = re.search(r'<script\s+id=["\']onsm-data-gzip["\']\s+type=["\']application/octet-stream["\']\s*>(.*?)</script>', s, re.S | re.I)
    if not m:
        raise RuntimeError('Embedded compressed article data not found in HTML input.')
    b64 = re.sub(r'\s+', '', m.group(1))
    data = json.loads(gzip.decompress(base64.b64decode(b64)).decode('utf-8'))
    recs = data['records']
    assert len(recs) == data['meta']['totalRecords'], 'HTML count mismatch'
    assert len(recs) == 536, f'Unexpected input article count: {len(recs)}'
    assert len({r['pmid'] for r in recs}) == 224, 'Unexpected unique-PMID count'
    assert [r['globalPosition'] for r in recs] == list(range(1, len(recs)+1)), 'Ordering mismatch'
    return data


def session():
    s = requests.Session()
    retry = Retry(total=5, connect=5, read=5, status=5,
                  backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=['GET', 'POST'], respect_retry_after_header=True)
    s.mount('https://', HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))
    s.headers.update({'User-Agent':'ONSM-ArticleAccessAudit/1.0 (academic literature checking; ' + (CONTACT_EMAIL or 'Colab') + ')',
                      'Accept':'application/json, application/xml, text/xml, */*'})
    return s


def get_json(s, url, params=None):
    response = s.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_xml(s, url, params=None):
    response = s.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return ET.fromstring(response.content)


def europe_pmc_batch(s, pmids):
    # Explicit OR query, with PMID/source verification on each returned row.
    terms = ' OR '.join('EXT_ID:' + str(p) for p in pmids)
    query = '(' + terms + ') AND SRC:MED'
    js = get_json(s, 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                  {'query':query, 'format':'json', 'resultType':'core', 'pageSize':max(len(pmids),25)})
    results = js.get('resultList', {}).get('result', [])
    wanted = set(map(str, pmids))
    return {str(r.get('pmid') or r.get('id')): r for r in results
            if str(r.get('pmid') or r.get('id')) in wanted and r.get('source','MED')=='MED'}


def full_text_urls(entry):
    value = (entry or {}).get('fullTextUrlList') or {}
    rows = value.get('fullTextUrl', []) if isinstance(value,dict) else []
    if isinstance(rows,dict): rows=[rows]
    out=[]
    for row in rows:
        if not isinstance(row,dict):continue
        url=row.get('url','')
        if url:
            out.append({'url':url,'availability':row.get('availability',''),
                        'documentStyle':row.get('documentStyle',''),
                        'site':row.get('site','')})
    return out


def is_explicitly_free(entry):
    if not entry:
        return False, 'No positive public full-text indication found', []
    links=full_text_urls(entry)
    if str(entry.get('isOpenAccess','')).upper()=='Y':
        return True, 'Europe PMC: isOpenAccess=Y', links
    if str(entry.get('isFree','')).upper()=='Y':
        return True, 'Europe PMC: isFree=Y', links
    for link in links:
        av = str(link.get('availability','')).lower()
        if av in ('open access','free','free full text'):
            return True, 'Europe PMC full-text link explicitly labelled free', links
    return False, 'No free-full-text indication confirmed by Europe PMC', links


def node_text(root, path):
    elem=root.find(path)
    return ''.join(elem.itertext()).strip() if elem is not None else ''


def pubmed_details(element):
    cit = element.find('./MedlineCitation')
    art = cit.find('./Article') if cit is not None else None
    if art is None:return None
    pmid=node_text(cit,'./PMID')
    authors=[]
    for a in art.findall('./AuthorList/Author'):
        last=node_text(a,'./LastName'); fore=node_text(a,'./ForeName') or node_text(a,'./Initials')
        name=' '.join(x for x in (fore,last) if x) or node_text(a,'./CollectiveName')
        if name: authors.append(name)
    year=(node_text(art,'./Journal/JournalIssue/PubDate/Year') or node_text(art,'./ArticleDate/Year'))
    if not year:
        md=node_text(art,'./Journal/JournalIssue/PubDate/MedlineDate')
        ma=re.search(r'(18|19|20)\d{2}',md)
        year=ma.group(0) if ma else ''
    pubmed_doi=''; pmcid=''
    for a in element.findall('.//ArticleIdList/ArticleId'):
        k=(a.get('IdType') or '').lower()
        v=(a.text or '').strip()
        if k=='doi':pubmed_doi=v
        if k=='pmc':pmcid=v
    for a in art.findall('./ELocationID'):
        if a.get('EIdType')=='doi' and not pubmed_doi:pubmed_doi=a.text or ''
    pagination = node_text(art,'./Pagination/MedlinePgn')
    if not pagination:
        pagination='; '.join((x.text or '') for x in art.findall('./ELocationID') if x.get('EIdType') in ('pii','page'))
    return {'pmid':pmid,'title':node_text(art,'./ArticleTitle'), 'authors':authors,
        'journal':node_text(art,'./Journal/Title'),
        'abbrevJournal':node_text(art,'./Journal/ISOAbbreviation'),
        'issn':node_text(art,'./Journal/ISSN'),
        'year':year,
        'pubDate':node_text(art,'./Journal/JournalIssue/PubDate'),
        'volume':node_text(art,'./Journal/JournalIssue/Volume'),
        'issue':node_text(art,'./Journal/JournalIssue/Issue'),
        'pages':pagination,'doi':pubmed_doi,'pmcid':pmcid,
        'publicationTypes':[(''.join(x.itertext()).strip()) for x in art.findall('./PublicationTypeList/PublicationType')],
        'abstract':' '.join(''.join(x.itertext()).strip() for x in art.findall('./Abstract/AbstractText'))}


def pubmed_batch(s, pmids):
    # PubMed EFetch is batched and rate-safe; no per-record scraping.
    params={'db':'pubmed','id':','.join(pmids),'retmode':'xml','tool':'ONSMArticleAudit'}
    if CONTACT_EMAIL:params['email']=CONTACT_EMAIL
    root=get_xml(s, 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',params)
    out={}
    for elem in root.findall('./PubmedArticle'):
        entry=pubmed_details(elem)
        if entry and entry['pmid']:out[entry['pmid']]=entry
    return out


def xml_full_text(s, pmcid):
    if not pmcid:return None, 'No PMCID is available'
    # Only retrieve publicly accessible fullTextXML, never bypass authentication.
    url=f'https://www.ebi.ac.uk/europepmc/webservices/rest/{quote(str(pmcid))}/fullTextXML'
    r=s.get(url,timeout=TIMEOUT)
    if r.status_code in (400,403,404,410):return None,f'No public fullTextXML ({r.status_code})'
    r.raise_for_status()
    try:root=ET.fromstring(r.content)
    except ET.ParseError:return None,'Provider returned non-XML response'
    if root.tag!='article' and not root.tag.endswith('}article'):
        return None,'Response was not a JATS article'
    pieces=[]
    # Preserve the narrative section structure and paragraph wording; figures and tables
    # are not reconstructed as images. They remain available through the source link.
    for sec in root.findall('.//body//sec'):
        title=node_text(sec,'./title')
        if title: pieces.append(('heading',title))
        for p in sec.findall('./p'):
            paragraph=' '.join(''.join(p.itertext()).split())
            if paragraph:pieces.append(('body',paragraph))
    # Include paragraphs not in any named section, when present.
    if not pieces:
        for p in root.findall('.//body//p'):
            paragraph=' '.join(''.join(p.itertext()).split())
            if paragraph:pieces.append(('body',paragraph))
    return (pieces or None),('Public XML retrieved' if pieces else 'XML did not contain article body paragraphs')


def save_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=1),encoding='utf-8')
    tmp.replace(path)


def hlabel(label):return 'رایگان (Free full text)' if label=='free' else 'نیازمند اشتراک یا دسترسی دانشگاهی / عدم تأیید نسخه رایگان'


def style_doc(doc):
    sec=doc.sections[0];sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.7)
    sec.left_margin=Inches(.83);sec.right_margin=Inches(.83)
    styles=doc.styles
    styles['Normal'].font.name='Arial';styles['Normal'].font.size=Pt(9.5)
    styles['Normal'].paragraph_format.space_after=Pt(5)
    styles['Heading 1'].font.name='Arial';styles['Heading 1'].font.size=Pt(18);styles['Heading 1'].font.color.rgb=RGBColor(21,51,85)
    styles['Heading 2'].font.name='Arial';styles['Heading 2'].font.size=Pt(12);styles['Heading 2'].font.color.rgb=RGBColor(26,80,128)
    return doc


def add_field(doc, label, value):
    if not value:return
    p=doc.add_paragraph()
    p.paragraph_format.keep_together=True
    p.add_run(label+': ').bold=True
    p.add_run(str(value))


def create_doc(data, meta, access, all_fulltexts):
    recs=data['records'];doc=style_doc(Document())
    doc.add_heading('ONSM | Full-Text Availability Audit',0)
    doc.add_paragraph('Records from 8 uploaded HTML sources; every occurrence and original category retained.')
    total=len(recs)
    free=sum(access[r['pmid']]['status']=='free' for r in recs)
    paid=total-free
    unique_count=len({r['pmid'] for r in recs})
    doc.add_paragraph(f'Records: {total}  |  Unique PMIDs: {unique_count}  |  Duplicate occurrences: {total-unique_count}')
    doc.add_paragraph(f'Free full text: {free} occurrences  |  No verified free full text: {paid} occurrences')
    doc.add_paragraph('Method: Europe PMC full-text availability and PubMed bibliographic verification (online). '
                      'A non-free classification means no verified freely available full text was found; it does NOT prove '
                      'that the publisher charges or that institutional access will succeed. Source errors are flagged per article.')
    doc.add_paragraph('Full-text bodies are included only where a publicly retrievable Europe PMC XML body exists. '
                      'Some articles classified free may have only a publisher/PMC link and no XML body. '
                      'Do not treat an abstract as the full text.')
    doc.add_paragraph('Checked (UTC): '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))
    doc.add_page_break()
    for idx,r in enumerate(recs,1):
        pmid=r['pmid'];m=meta.get(pmid,{}) or {};ac=access[pmid]
        title=m.get('title') or r.get('title','Untitled article')
        doc.add_heading(f'{idx:03d}. {title}',level=2)
        add_field(doc,'Article occurrence',f"{idx} / {len(recs)} | Original file: {r.get('sourceFile','')} | Original position: {r.get('sourcePosition','')}")
        add_field(doc,'Search category',r.get('category'))
        add_field(doc,'Repeated PMID',f"{r.get('combinedDuplicateIndex',1)} of {r.get('combinedDuplicateTotal',1)}")
        authors=m.get('authors') or r.get('authors',[])
        add_field(doc,'Authors','; '.join(authors))
        add_field(doc,'Journal',m.get('journal') or m.get('abbrevJournal') or 'Not supplied in source')
        add_field(doc,'Publication',f"{m.get('year') or r.get('year','')} | Volume: {m.get('volume','—')} | Issue: {m.get('issue','—')} | Pages/eLocator: {m.get('pages','—')}")
        add_field(doc,'Date',m.get('pubDate') or r.get('pubdate',''))
        add_field(doc,'ISSN',m.get('issn',''))
        add_field(doc,'Article type(s)','; '.join(m.get('publicationTypes') or r.get('types',[])))
        add_field(doc,'PMID',pmid)
        add_field(doc,'DOI',m.get('doi') or r.get('doi',''))
        pmcid=m.get('pmcid') or ac.get('pmcid')
        add_field(doc,'PMCID',pmcid)
        add_field(doc,'PubMed',f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/')
        if pmcid:add_field(doc,'PMC',f'https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/')
        doi=m.get('doi') or r.get('doi')
        if doi:add_field(doc,'DOI link','https://doi.org/'+doi)
        add_field(doc,'FULL-TEXT ACCESS',hlabel(ac['status']))
        add_field(doc,'Access evidence',ac.get('reason'))
        if ac.get('lookup_error'):
            add_field(doc,'Verification warning','Europe PMC lookup failed or record was absent: '+ac['lookup_error'])
        links=ac.get('links',[])
        if links:
            for l in links[:5]:add_field(doc,'Provider full-text URL',l.get('url',''))
        if ac['status']!='free':
            doc.add_paragraph('Full article text: Not inserted. No free full-text copy was verified; consult the publisher or institutional access.')
        else:
            bits=all_fulltexts.get(pmid,[])
            if bits:
                doc.add_heading('Full article text (public XML)',level=2)
                for tp,t in bits:
                    if tp=='heading':doc.add_heading(t,level=3)
                    else:doc.add_paragraph(t)
            else:
                doc.add_paragraph('Full article text: A free-to-read version was identified, but public structured XML '
                                  'was not available. Use the full-text URL above. Abstract text is not substituted.')
        sep=doc.add_paragraph('—'*36)
        sep.paragraph_format.space_after=Pt(12)
        if idx%25==0:
            print(f'Word: {idx}/{len(recs)} records',flush=True)
    doc.save(OUTPUT_DOCX)
    print('Saved',OUTPUT_DOCX,'size',OUTPUT_DOCX.stat().st_size,flush=True)


def write_csv(data, metadata, status):
    cols=['record','source_file','source_row','search_category','duplicate_occurrence','duplicate_total','title',
          'authors','journal','year','volume','issue','pages','issn','pmid','doi','pmcid','classification','reason','verification_error',
          'pubmed_link','provider_full_text_links']
    with OUTPUT_CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in data['records']:
            p=r['pmid'];m=metadata.get(p,{}) or {};a=status[p]
            w.writerow({'record':r['globalPosition'],'source_file':r['sourceFile'],'source_row':r['sourcePosition'],
                        'search_category':r['category'],'duplicate_occurrence':r['combinedDuplicateIndex'],
                        'duplicate_total':r['combinedDuplicateTotal'],'title':m.get('title') or r.get('title'),
                        'authors':'; '.join(m.get('authors') or r.get('authors',[])),
                        'journal':m.get('journal',''),'year':m.get('year') or r.get('year'),
                        'volume':m.get('volume',''),'issue':m.get('issue',''),'pages':m.get('pages',''),'issn':m.get('issn',''),
                        'pmid':p,'doi':m.get('doi') or r.get('doi',''),'pmcid':m.get('pmcid') or a.get('pmcid',''),
                        'classification':hlabel(a['status']),'reason':a.get('reason'), 'verification_error':a.get('lookup_error',''),
                        'pubmed_link':f'https://pubmed.ncbi.nlm.nih.gov/{p}/',
                        'provider_full_text_links':' | '.join(l.get('url','') for l in a.get('links',[]))})


def run():
    if not INPUT.exists():raise FileNotFoundError(f'Cannot find {INPUT}. Download both HTML and PY into the same folder.')
    data=load_input(INPUT); recs=data['records']
    pmids=list(dict.fromkeys(str(r['pmid']) for r in recs))
    print(f'Source audit: {len(recs)} occurrences, {len(pmids)} unique PMIDs; duplicates preserved.',flush=True)
    s=session();cache={'pmc':{},'pubmed':{}}
    if CACHE_FILE.exists():
        try:
            cache=json.loads(CACHE_FILE.read_text(encoding='utf-8'))
            cache.setdefault('pmc',{});cache.setdefault('pubmed',{})
            print('Resumed from cache:',CACHE_FILE,flush=True)
        except Exception as e:print('Cache read error; fresh scan:',e,flush=True)
    for n in range(0,len(pmids),BATCH_SIZE):
        batch=pmids[n:n+BATCH_SIZE]
        missing=[x for x in batch if x not in cache['pmc']]
        if missing:
            try:
                epmc=europe_pmc_batch(s,missing)
                for x in missing:cache['pmc'][x]={'data':epmc.get(x),'error':'' if x in epmc else 'No Europe PMC record found'}
                print(f'Europe PMC: batch {1+n//BATCH_SIZE}, {len(epmc)}/{len(missing)} matched',flush=True)
            except Exception as e:
                print(f'Europe PMC batch failed; fallback to one-by-one: {e}',flush=True)
                for x in missing:
                    try:
                        response=europe_pmc_batch(s,[x]);cache['pmc'][x]={'data':response.get(x),'error':'' if x in response else 'No Europe PMC record found'}
                    except Exception as ex:
                        cache['pmc'][x]={'data':None,'error':repr(ex)}
                    time.sleep(0.2)
        missing_pub=[x for x in batch if x not in cache['pubmed']]
        if missing_pub:
            try:
                entries=pubmed_batch(s,missing_pub)
                for x in missing_pub:cache['pubmed'][x]=entries.get(x,{})
                print(f'PubMed: batch {1+n//BATCH_SIZE}, {len(entries)}/{len(missing_pub)} found',flush=True)
            except Exception as e:
                print('PubMed metadata temporarily unavailable, retaining source metadata:',repr(e),flush=True)
                for x in missing_pub:cache['pubmed'][x]={}
        save_json(CACHE_FILE,cache)
        time.sleep(.44)  # requests to NCBI must stay below 3 per second without a key
    access={}
    for pmid in pmids:
        info=cache['pmc'].get(pmid,{})
        entry=info.get('data')
        free,reason,links=is_explicitly_free(entry)
        access[pmid]={'status':'free' if free else 'subscription',
                      'reason':reason,'links':links,
                      'pmcid':(entry or {}).get('pmcid') or cache['pubmed'].get(pmid,{}).get('pmcid',''),
                      'lookup_error':info.get('error','')}
    free_n=sum(access[p]['status']=='free' for p in pmids)
    print(f'Unique PMID access: free={free_n}; no confirmed free copy={len(pmids)-free_n}',flush=True)
    TEXT_CACHE.mkdir(exist_ok=True)
    all_fulltexts={}
    if FETCH_PUBLIC_FULL_TEXT:
        for i,pmid in enumerate(pmids,1):
            a=access[pmid]
            if a['status']!='free':continue
            pc=a.get('pmcid');
            if not pc:continue
            cache_path=TEXT_CACHE/f'{pc}.json'
            if cache_path.exists():
                try:full=json.loads(cache_path.read_text(encoding='utf-8'));all_fulltexts[pmid]=full.get('text') or [];continue
                except Exception:pass
            try:
                bits,message=xml_full_text(s,pc)
                all_fulltexts[pmid]=bits or []
                save_json(cache_path,{'text':all_fulltexts[pmid],'note':message})
                if bits:print(f'Public article text {i}/{len(pmids)}: {pc} ({len(bits)} blocks)',flush=True)
                time.sleep(.2)
            except Exception as e:
                print(f'Public XML not retrievable for {pc}: {e}',flush=True)
    write_csv(data,cache['pubmed'],access)
    create_doc(data,cache['pubmed'],access,all_fulltexts)
    print('CSV saved:',OUTPUT_CSV,OUTPUT_CSV.stat().st_size,'bytes')
    print('Records in outputs:',len(recs),'(duplicates preserved)')
    try:
        from google.colab import files
        files.download(str(OUTPUT_DOCX))
        files.download(str(OUTPUT_CSV))
    except ImportError:
        print('Not Colab: outputs are in',Path.cwd())


if __name__=='__main__':
    try:run()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
