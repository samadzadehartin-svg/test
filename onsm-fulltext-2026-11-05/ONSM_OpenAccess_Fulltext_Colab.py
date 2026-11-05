#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONSM: acquire openly licensed complete JATS texts and collect them into Word.

Use with the merged ONSM HTML file. Abstract-only entries are NEVER accepted.
Metadata and full text are retrieved live via official Europe PMC and PMC APIs.
"""
import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

def install_dependencies():
    dependencies = {'requests':'requests','docx':'python-docx','lxml':'lxml'}
    missing = [pkg for mod,pkg in dependencies.items() if importlib.util.find_spec(mod) is None]
    if missing:
        print('Installing '+', '.join(missing), flush=True)
        subprocess.check_call([sys.executable,'-m','pip','install','-q',*missing])

install_dependencies()
import requests
from lxml import etree
from docx import Document
from docx.shared import Cm, Pt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EUROPE = 'https://www.ebi.ac.uk/europepmc/webservices/rest'
PMC_OAI = 'https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/'
USER_AGENT = 'ONSM-OA-Research-Collector/1.0 (noncommercial academic research)'
def session_create():
    sess=requests.Session()
    sess.headers.update({'User-Agent':USER_AGENT,'Accept':'application/json,application/xml,text/xml;q=0.9,*/*;q=0.5'})
    retries=Retry(total=3,connect=3,read=3,backoff_factor=1.2,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=['GET'],respect_retry_after_header=True)
    sess.mount('https://',HTTPAdapter(max_retries=retries,pool_connections=2,pool_maxsize=2))
    return sess

def articles_from_html(filename):
    source=Path(filename).read_text(encoding='utf-8')
    m=re.search(r'<script\s+id=["\']onsm-data["\']\s+type=["\']application/json["\']>(.*?)</script>',source,re.S|re.I)
    if not m:
        raise ValueError('No onsm-data present: download the combined HTML.')
    data=json.loads(m.group(1))
    seen=set(); result=[]
    for article in data.get('articles',[]):
        pmid=str(article.get('pmid','')).strip()
        if re.fullmatch(r'\d{1,12}',pmid) and pmid not in seen:
            result.append(article);seen.add(pmid)
    print('Original occurrences:',data.get('recordCount'),'Unique PMIDs:',len(result),flush=True)
    if not result:
        raise ValueError('No valid PMIDs found in input')
    return result

def article_metadata(sess,pmid):
    r=sess.get(EUROPE+'/search',params={'query':f'EXT_ID:{pmid} AND SRC:MED',
               'format':'json','resultType':'core','pageSize':2},timeout=(12,50))
    r.raise_for_status()
    return next((x for x in r.json().get('resultList',{}).get('result',[])
                 if str(x.get('id'))==str(pmid) and x.get('source')=='MED'),None)

def download_europe_xml(sess,pmcid):
    r=sess.get(f'{EUROPE}/{pmcid}/fullTextXML',timeout=(12,90),
               headers={'Accept':'application/xml,text/xml'})
    if r.status_code in (400,403,404,410):
        return None
    r.raise_for_status()
    return r.content if b'<article' in r.content[:1000] else None

def download_pmc_oai_xml(sess,pmcid):
    number=re.sub(r'\D','',str(pmcid))
    if not number:
        return None
    r=sess.get(PMC_OAI,params={'verb':'GetRecord',
        'identifier':f'oai:pubmedcentral.nih.gov:{number}',
        'metadataPrefix':'pmc'},timeout=(12,90),
        headers={'Accept':'application/xml,text/xml'})
    if r.status_code in (400,403,404,410):
        return None
    r.raise_for_status()
    doc=etree.fromstring(r.content,parser=etree.XMLParser(resolve_entities=False,no_network=True))
    found=doc.xpath('//*[local-name()="metadata"]/*[local-name()="article"]')
    return etree.tostring(found[0],encoding='utf-8') if found else None

def tagname(element):
    return etree.QName(element).localname if isinstance(element.tag,str) else ''

def content(element):
    # No paraphrasing or translation; normalize XML whitespace only.
    return re.sub(r'\s+',' ',''.join(element.itertext())).strip()

def read_blocks(element,blocks,level=2):
    for e in element:
        tag=tagname(e)
        if tag in ('sec','sub-article','app','ack','boxed-text','notes','glossary',
                   'fn-group','def-list','table-wrap-group','supplementary-material'):
            read_blocks(e,blocks,level+(tag=='sec'))
        elif tag=='title':
            s=content(e)
            if s:blocks.append(('heading'+str(min(4,int(level))),s))
        elif tag in ('p','statement','speech'):
            s=content(e)
            if s:blocks.append(('text',s))
        elif tag=='list':
            for item in e:
                if tagname(item)=='list-item':
                    s=content(item)
                    if s:blocks.append(('bullet',s))
        elif tag=='table-wrap':
            label=e.find('./label'); caption=e.find('./caption')
            s=' '.join(x for x in [content(label) if label is not None else '',
                                   content(caption) if caption is not None else ''] if x)
            if s:blocks.append(('caption',s))
            for row in e.xpath('.//*[local-name()="tr"]'):
                cells=[content(cell) for cell in row if tagname(cell) in ('td','th')]
                if cells:blocks.append(('table',' | '.join(cells)))
            for footer in e.xpath('./*[local-name()="table-wrap-foot"]'):
                s=content(footer)
                if s:blocks.append(('text',s))
        elif tag=='fig':
            lab=e.find('./label'); cap=e.find('./caption')
            s=' '.join(x for x in [content(lab) if lab is not None else '',
                                   content(cap) if cap is not None else ''] if x)
            if s:blocks.append(('caption',s))
        elif tag in ('disp-formula','inline-formula','preformat','code'):
            s=content(e)
            if s:blocks.append(('formula',s))
        elif tag=='ref':
            s=content(e)
            if s:blocks.append(('reference',s))
        elif tag=='label':
            s=content(e)
            if s:blocks.append(('text',s))
        elif len(e):
            read_blocks(e,blocks,level)

def full_text_xml_to_blocks(xml,pmid,pmcid):
    root=etree.fromstring(xml,parser=etree.XMLParser(resolve_entities=False,
                    no_network=True,huge_tree=False,remove_comments=True))
    articles=[root] if tagname(root)=='article' else root.xpath('//*[local-name()="article"]')
    if not articles:raise ValueError('Not a JATS full-text article')
    root=articles[0]
    for tag in root.xpath('.//*[local-name()="article-id"][@pub-id-type="pmid"]'):
        if content(tag) and content(tag)!=str(pmid):
            raise ValueError('Mismatched PMID: '+content(tag))
    for tag in root.xpath('.//*[local-name()="article-id"][@pub-id-type="pmc"]'):
        a=re.sub(r'\D','',content(tag));b=re.sub(r'\D','',str(pmcid))
        if a and b and a!=b:raise ValueError('Mismatched PMCID: '+a)
    body=root.xpath('./*[local-name()="body"]')
    if not body:raise ValueError('Abstract or metadata only: missing JATS body')
    blocks=[]
    for ab in root.xpath('./*[local-name()="front"]/*[local-name()="article-meta"]/*[local-name()="abstract"]'):
        blocks.append(('heading2','Abstract'));read_blocks(ab,blocks,3)
    blocks.append(('heading2','Full Text'))
    read_blocks(body[0],blocks,3)
    back=root.xpath('./*[local-name()="back"]')
    if back:
        blocks.append(('heading2','References and Back Matter'))
        read_blocks(back[0],blocks,3)
    count=sum(len(s.split()) for typ,s in blocks if typ in ('text','bullet','table','formula'))
    if count<40:raise ValueError('Too little article body to qualify as full text')
    return blocks

def new_document():
    doc=Document()
    section=doc.sections[0]
    section.top_margin=Cm(2);section.bottom_margin=Cm(2)
    section.left_margin=Cm(2.3);section.right_margin=Cm(2.3)
    doc.styles['Normal'].font.name='Calibri'
    doc.styles['Normal'].font.size=Pt(10.5)
    doc.styles['Normal'].paragraph_format.space_after=Pt(6)
    for name in ('Title','Heading 1','Heading 2','Heading 3','Heading 4'):
        doc.styles[name].font.name='Calibri'
    return doc

def save_article(doc,article,meta,blocks,n):
    if n>1:doc.add_page_break()
    doc.add_heading(f'{n}. {article.get("title") or meta.get("title")}',level=1)
    info=meta.get('journalInfo') or {}
    journal=meta.get('journalTitle') or (info.get('journal') or {}).get('title') or ''
    issued=meta.get('firstPublicationDate') or article.get('pubdate') or article.get('year') or ''
    entries=[
        'Authors: '+'; '.join(article.get('authors') or []),
        'Journal: '+journal if journal else '',
        'Published: '+str(issued) if issued else '',
        'PMID: '+str(article['pmid']),
        'PMCID: '+str(meta['pmcid']) if meta.get('pmcid') else '',
        'DOI: '+str(article['doi']) if article.get('doi') else '',
        'PubMed: https://pubmed.ncbi.nlm.nih.gov/'+str(article['pmid'])+'/',
        'Full-text source: https://europepmc.org/articles/'+str(meta['pmcid']) if meta.get('pmcid') else ''
    ]
    for s in entries:
        if s:doc.add_paragraph(s)
    for kind,s in blocks:
        if kind.startswith('heading'):
            doc.add_heading(s,level=max(2,min(4,int(kind[-1]))))
        elif kind=='bullet':
            doc.add_paragraph(s,style='List Bullet')
        else:
            p=doc.add_paragraph(s)
            if kind=='caption':p.style='Caption'

def save_log(filename,rows):
    with open(filename,'w',newline='',encoding='utf-8-sig') as stream:
        w=csv.DictWriter(stream,fieldnames=['pmid','title','status','pmcid','detail'])
        w.writeheader();w.writerows(rows)

def run(args):
    articles=articles_from_html(args.html)
    if args.limit:articles=articles[:args.limit]
    if args.check_only:
        print('HTML validated. No online requests were made.')
        return
    doc=new_document()
    sess=session_create()
    rows=[];ok=0
    print('Checking each PMID live and including only licensed OA JATS full text.',flush=True)
    for i,article in enumerate(articles,1):
        pmid=str(article['pmid']);pmcid='';detail='';status='not_checked'
        try:
            meta=article_metadata(sess,pmid)
            if not meta:
                status='not_found';detail='No matching MED record'
            else:
                pmcid=str(meta.get('pmcid') or '')
                if meta.get('isOpenAccess')!='Y':
                    status='not_open_access'
                    detail='Europe PMC has no reusable open-access full text'
                elif not pmcid:
                    status='no_pmcid';detail='Open access flag without PMC ID'
                else:
                    xml=None;error=''
                    try:xml=download_europe_xml(sess,pmcid)
                    except (requests.RequestException,etree.XMLSyntaxError) as exc:
                        error='Europe PMC: '+str(exc)[:150]
                    if not xml:
                        try:xml=download_pmc_oai_xml(sess,pmcid)
                        except (requests.RequestException,etree.XMLSyntaxError) as exc:
                            error+=' | PMC OAI: '+str(exc)[:150]
                    if xml:
                        blocks=full_text_xml_to_blocks(xml,pmid,pmcid)
                        save_article(doc,article,meta,blocks,ok+1)
                        ok+=1;status='included_full_text';detail=f'{len(blocks)} content blocks'
                    else:
                        status='full_text_xml_unavailable'
                        detail=error or 'Neither official endpoint returned OA full text XML'
        except (requests.RequestException,ValueError,etree.XMLSyntaxError,KeyError,TypeError) as exc:
            status='error_or_incomplete';detail=str(exc)[:250]
        rows.append({'pmid':pmid,'title':article.get('title',''),'status':status,
                    'pmcid':pmcid,'detail':detail})
        print(f'[{i}/{len(articles)}] {pmid} -> {status}',flush=True)
        if ok and ok%args.save_every==0 and status=='included_full_text':
            doc.save(args.output)
        if i%10==0:save_log(args.log,rows)
        if i<len(articles):time.sleep(args.delay)
    save_log(args.log,rows)
    if ok:
        doc.save(args.output)
        print('Word created:',args.output,'Papers:',ok,flush=True)
        if args.download:
            try:
                from google.colab import files
                files.download(args.output)
            except ImportError:
                print('Automatic download is available in Colab only.')
    else:
        print('No valid OA full text retrieved; no abstract-only Word generated.')
    counts={}
    for row in rows:counts[row['status']]=counts.get(row['status'],0)+1
    print('Verification CSV:',args.log,'Results:',counts)
    print('Coverage: OA full-text XML via Europe PMC / PMC; some publisher-only free texts may not be found.')

def main():
    p=argparse.ArgumentParser(description='ONSM full-text to Word; no abstracts-only')
    p.add_argument('--html',default='ONSM_716_Records_244_Unique.html')
    p.add_argument('--output',default='ONSM_OpenAccess_FullTexts.docx')
    p.add_argument('--log',default='ONSM_Access_Log.csv')
    p.add_argument('--download',action='store_true')
    p.add_argument('--limit',type=int,default=0,help='For testing; 0 means all PMIDs')
    p.add_argument('--check-only',action='store_true',help='Only validate list without network')
    p.add_argument('--save-every',type=int,default=10)
    p.add_argument('--delay',type=float,default=0.6)
    args=p.parse_args()
    if args.save_every<1 or args.delay<0:p.error('Invalid save-every or delay')
    run(args)
if __name__=='__main__':
    main()
