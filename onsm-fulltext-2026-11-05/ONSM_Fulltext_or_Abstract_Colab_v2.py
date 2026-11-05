#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONSM: compile a 244-paper Word with free full text when available, otherwise abstract.

Live check per PMID via Europe PMC and PMC; keep 244 unique articles from
716 source occurrences. This tool never bypasses paywalls. It logs any errors
and preserves a fallback abstract or at minimum article metadata.
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

def save_article(doc, article, meta, blocks, n, status, source_url=''):
    """Write exactly one article, using original metadata and retrieved text."""
    if n > 1:
        doc.add_page_break()
    meta = meta or {}
    doc.add_heading(f'{n}. {article.get("title") or meta.get("title") or "Untitled article"}', level=1)
    info = meta.get('journalInfo') or {}
    journal = meta.get('journalTitle') or ''
    if not journal and isinstance(info, dict):
        j = info.get('journal') or {}
        if isinstance(j, dict):
            journal = j.get('title') or ''
        elif isinstance(j, str):
            journal = j
    issued = meta.get('firstPublicationDate') or article.get('pubdate') or article.get('year') or ''
    names = article.get('authors') or []
    if isinstance(names, str):
        names = [names]
    pmcid = str(meta.get('pmcid') or '')
    entries = [
        'Access result: ' + status,
        'Authors: ' + '; '.join(str(x) for x in names),
        'Journal: ' + journal if journal else '',
        'Published: ' + str(issued) if issued else '',
        'PMID: ' + str(article['pmid']),
        'PMCID: ' + pmcid if pmcid else '',
        'DOI: ' + str(article.get('doi') or meta.get('doi') or '') if (article.get('doi') or meta.get('doi')) else '',
        'Publication type: ' + str(article.get('articleClass') or ''),
        'PubMed: https://pubmed.ncbi.nlm.nih.gov/' + str(article['pmid']) + '/',
        'Full-text source: ' + source_url if source_url else '',
    ]
    for entry in entries:
        if entry:
            doc.add_paragraph(entry)
    for kind, text in blocks:
        if not text:
            continue
        if kind.startswith('heading'):
            doc.add_heading(text, level=max(2, min(4, int(kind[-1]))))
        elif kind == 'bullet':
            doc.add_paragraph(text, style='List Bullet')
        else:
            p = doc.add_paragraph(text)
            if kind == 'caption':
                p.style = 'Caption'

def abstract_fallback(article, meta):
    """Prefer the original source abstract. Never invent an abstract."""
    raw = article.get('abstract') or (meta or {}).get('abstractText') or ''
    if not isinstance(raw, str):
        raw = str(raw)
    # Europe PMC metadata can embed HTML tags; the input HTML abstract is plain text.
    if not article.get('abstract'):
        raw = re.sub(r'<[^>]+>', ' ', raw)
        import html as html_module
        raw = html_module.unescape(raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    if raw:
        return [('heading2', 'Abstract (full text not retrieved)'), ('text', raw)], 'ABSTRACT_ONLY'
    return [('heading2', 'Abstract'), ('text', 'Abstract unavailable in source HTML and public metadata.')], 'METADATA_ONLY'

def save_log(filename, rows):
    fields = ['pmid', 'title', 'status', 'pmcid', 'detail']
    with open(filename, 'w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def run(args):
    articles = articles_from_html(args.html)
    if args.limit:
        articles = articles[:args.limit]
    if args.check_only:
        print('Validated HTML: no network requests made.', flush=True)
        return
    doc = new_document()
    sess = session_create()
    counts = {'FULL_TEXT':0, 'ABSTRACT_ONLY':0, 'METADATA_ONLY':0}
    rows = []
    print(f'Starting live verification of {len(articles)} unique articles.', flush=True)
    print('Policy: free full text -> full JATS text; otherwise -> original abstract.', flush=True)
    for i, article in enumerate(articles, 1):
        pmid = str(article['pmid'])
        meta = {}
        pmcid = ''
        errors = []
        blocks = None
        source_url = ''
        status = ''
        try:
            try:
                meta = article_metadata(sess, pmid) or {}
                if not meta:
                    errors.append('No live PubMed metadata returned; using embedded records')
            except Exception as exc:
                errors.append('Metadata request failed: ' + str(exc)[:180])
            pmcid = str(meta.get('pmcid') or '')
            # Public JATS endpoints are used, irrespective of the index's OA flag:
            # a PMCID can be free-to-read although not classified as fully OA.
            if pmcid:
                xml = None
                try:
                    xml = download_europe_xml(sess, pmcid)
                except Exception as exc:
                    errors.append('Europe PMC XML: ' + str(exc)[:120])
                if not xml:
                    try:
                        xml = download_pmc_oai_xml(sess, pmcid)
                    except Exception as exc:
                        errors.append('PMC OAI XML: ' + str(exc)[:120])
                if xml:
                    try:
                        blocks = full_text_xml_to_blocks(xml, pmid, pmcid)
                        source_url = 'https://europepmc.org/articles/' + pmcid
                        status = 'FULL_TEXT'
                    except Exception as exc:
                        errors.append('Full-text parse failed: ' + str(exc)[:180])
            if blocks is None:
                blocks, status = abstract_fallback(article, meta)
                if not pmcid:
                    errors.append('No PMCID in live metadata')
                elif not errors:
                    errors.append('Public full-text XML was not accessible')
        except Exception as exc:
            # Per-PMID safety net: never let an unavailable source abort all articles.
            errors.append('Unexpected paper error: ' + str(exc)[:200])
            blocks, status = abstract_fallback(article, meta)
        try:
            save_article(doc, article, meta, blocks, i, status, source_url)
        except Exception as exc:
            # Prevent metadata variations from blocking the entire corpus.
            print('Writing warning for PMID', pmid, str(exc)[:160], flush=True)
            if i > 1:
                doc.add_page_break()
            doc.add_heading(str(i) + '. ' + str(article.get('title') or pmid), level=1)
            doc.add_paragraph('PMID: ' + pmid)
            doc.add_paragraph('Access result: ' + status)
            for kind, value in blocks:
                doc.add_paragraph(str(value))
            errors.append('Word formatting fallback: ' + str(exc)[:160])
        counts[status] = counts.get(status, 0) + 1
        rows.append({'pmid':pmid, 'title':article.get('title') or '',
                     'status':status, 'pmcid':pmcid,
                     'detail':' | '.join(errors) or 'Retrieved successfully'})
        print(f'[{i}/{len(articles)}] PMID {pmid} -> {status}', flush=True)
        if i % args.save_every == 0:
            doc.save(args.output)
            save_log(args.log, rows)
            print(f'Checkpoint saved: {i} articles.', flush=True)
        if i < len(articles):
            time.sleep(args.delay)
    doc.save(args.output)
    save_log(args.log, rows)
    print('SUCCESS: Word created at:', str(Path(args.output).resolve()), flush=True)
    print('Total:',len(rows), 'Full text:', counts['FULL_TEXT'],
          'Abstract:', counts['ABSTRACT_ONLY'], 'Metadata only:', counts['METADATA_ONLY'],
          flush=True)
    print('Detailed log:', str(Path(args.log).resolve()), flush=True)
    print('Note: publisher-only free pages without public XML may fall back to abstract.', flush=True)
    if args.download:
        try:
            from google.colab import files
            files.download(args.output)
        except Exception as exc:
            print('Download in subprocess may be unavailable: '+str(exc)[:120],
                  'Use files.download() in a notebook cell.', flush=True)

def main():
    p=argparse.ArgumentParser(description='ONSM full text if free, otherwise source abstract')
    p.add_argument('--html',default='ONSM_716_Records_244_Unique.html')
    p.add_argument('--output',default='ONSM_All_244_Fulltext_or_Abstract.docx')
    p.add_argument('--log',default='ONSM_244_Access_Report.csv')
    p.add_argument('--download',action='store_true')
    p.add_argument('--limit',type=int,default=0,help='For testing; 0 means all PMIDs')
    p.add_argument('--check-only',action='store_true',help='Only validate list without network')
    p.add_argument('--save-every',type=int,default=5)
    p.add_argument('--delay',type=float,default=0.4)
    args=p.parse_args()
    if args.save_every<1 or args.delay<0:p.error('Invalid save-every or delay')
    run(args)
if __name__=='__main__':
    main()
