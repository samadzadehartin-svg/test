#!/usr/bin/env python3
# Standalone assembled variant of the three tested modules
"""Official API retrieval helpers: Europe PMC JATS and NCBI BioC OA."""
import json,re,time,threading
from pathlib import Path
from xml.etree import ElementTree as ET
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
BASE='https://www.ebi.ac.uk/europepmc/webservices/rest'
BIOC='https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json'
TERMS=[
'bdnf trkb neurotrophic glutamate ampa nmda inflammation microglia actin cofilin cytoskeleton spine',
'stress environment exercise sleep diet nutrition omega microbiota hormone estrogen cortisol dendritic spine',
'suicide suicidal depression postmortem hippocampus prefrontal synaptic spine morphology',
'molecular neurotrophic synaptic remodeling spine plasticity depression clinical outcomes',
'biomarker antidepressant response suicide risk serum blood plasma miRNA exosome neuroimaging',
'precision personalized translational antidepressant ketamine treatment clinical therapeutic target'
]
_lock=threading.Lock();_last=[0];_thread=threading.local()
def sess():
    if not hasattr(_thread,'s'):
        s=Session()
        s.headers['User-Agent']='AcademicResearchIntegrative/1.0 (OA API text extraction)'
        retry=Retry(total=3,backoff_factor=1.2,status_forcelist=[429,500,502,503,504],
                    allowed_methods=['GET'],respect_retry_after_header=True)
        s.mount('https://',HTTPAdapter(max_retries=retry))
        _thread.s=s
    return _thread.s
def get(url,params=None,timeout=40):
    with _lock:
        d=.60-(time.monotonic()-_last[0])
        if d>0:time.sleep(d)
        _last[0]=time.monotonic()
    try:
        r=sess().get(url,params=params,timeout=timeout)
        if r.status_code in (403,404,410):return None
        r.raise_for_status()
        return r
    except Exception as e:
        print('WARN API:',str(e)[:110],flush=True)
        return None
def clean(t):return re.sub(r'\s+',' ',re.sub(r'<[^>]*>',' ',t or '')).strip()
def metadata(pmid):
    r=get(BASE+'/search',{'query':'EXT_ID:'+pmid+' AND SRC:MED','format':'json','resultType':'core','pageSize':1})
    if r is None:return {}
    try:
        hits=r.json().get('resultList',{}).get('result',[])
        if not hits or str(hits[0].get('id'))!=pmid:return {}
        q=hits[0];j=q.get('journalInfo') or {}
        return dict(title=clean(q.get('title')),authors=clean(q.get('authorString')),
          journal=clean(q.get('journalTitle') or (j.get('journal') or {}).get('title')),
          year=q.get('pubYear') or '',doi=q.get('doi') or '',pmcid=q.get('pmcid') or '',
          volume=j.get('journalIssueId') or '',pages=q.get('pageInfo') or '',
          abstract=clean(q.get('abstractText') or ''))
    except Exception as e:
        print('WARN metadata',pmid,str(e)[:80]);return {}
def jats(xml):
    root=ET.fromstring(xml)
    body=next((x for x in root.iter() if x.tag.split('}')[-1]=='body'),None)
    out=[];seen=set()
    if body is None:return out
    def walk(node,section=''):
        name=node.tag.split('}')[-1]
        if name in ('fig','table-wrap','ref-list','back','supplementary-material','disp-formula'):return
        if name=='sec':
            title=next((x for x in node if x.tag.split('}')[-1]=='title'),None)
            if title is not None:section=clean(''.join(title.itertext()))[:150]
        if name=='p':
            t=clean(''.join(node.itertext()))
            if len(t)>45 and t not in seen:
                seen.add(t);out.append({'section':section,'text':t})
            return
        for child in node:
            if child.tag.split('}')[-1] not in ('title','label'):walk(child,section)
    walk(body)
    return out
def bioc(obj):
    try:
        doc=obj[0] if isinstance(obj,list) else obj
        if doc.get('documents'):doc=doc['documents'][0]
        out=[];seen=set();section=''
        for block in doc.get('passages',[]):
            kind=str((block.get('infons') or {}).get('type','')).lower()
            txt=clean(block.get('text'))
            if kind in ('section_title','section header'):section=txt
            if kind in ('paragraph','body','text') and len(txt)>45 and txt not in seen:
                seen.add(txt);out.append({'section':section,'text':txt})
        return out
    except:return []
def oa_body(pmid,pmcid):
    if pmcid:
        r=get(BASE+'/'+pmcid+'/fullTextXML',timeout=60)
        if r is not None:
            try:
                p=jats(r.text)
                if p:return p,'Europe PMC OA JATS XML'
            except Exception as e:print('WARN JATS',pmid,str(e)[:60])
    r=get(BIOC+'/'+pmid+'/unicode',timeout=50)
    if r is not None:
        try:
            p=bioc(r.json())
            if p:return p,'NCBI BioC Open Access'
        except:pass
    return [],''
def relevant(paras,section):
    kw=TERMS[max(0,min(5,section-1))].split()
    cand=[p for p in paras if len(p['text'].split())>35] or paras
    if not cand:return {'section':'','text':''}
    def s(p):
        t=p['text'].lower();n=len(t.split())
        return sum(t.count(w) for w in kw)+2*sum(t.count(x) for x in ('depress','suicid','spine','synap'))+(2 if 45<n<250 else 0)
    return max(cand,key=s)
def process(item,cache):
    file=Path(cache)/(item['pmid']+'.json')
    if file.exists():
        try:return json.loads(file.read_text(encoding='utf8'))
        except:pass
    meta=metadata(item['pmid'])
    pmcid=item.get('pmcid') or meta.get('pmcid') or ''
    body,source=oa_body(item['pmid'],pmcid)
    paragraph=relevant(body,item['section'])
    origin='FULL_TEXT'
    if not paragraph['text']:
        paragraph={'section':'Abstract','text':meta.get('abstract') or ''}
        origin='ABSTRACT_ONLY' if paragraph['text'] else 'NO_TEXT'
    result={**item,**meta,'pmid':item['pmid'],'pmcid':pmcid,
            'body':body,'oa_source':source,'paragraph':paragraph,'source_flag':origin}
    file.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
    return result


"""Create reference/evidence and available open-access full-text Word documents."""
import csv,json,zipfile
from pathlib import Path
from docx import Document
from docx.shared import Pt,Inches
HEADINGS=[
'Neurotrophic signaling / neurotransmission / inflammation / cytoskeleton',
'Environmental, behavioral, hormonal, and nutritional influences',
'Shared and distinct mechanisms: depression and suicidal behavior',
'Integrative molecular / dendritic-spine / clinical model',
'Biomarkers, depression, treatment response, and suicide vulnerability',
'Translational implications in precision psychiatry'
]
def cite(r):
    return (str(r.get('authors',''))+'. '+str(r.get('title','[title not retrieved]'))+
            ' '+str(r.get('journal',''))+'. '+str(r.get('year',''))+
            ';'+str(r.get('volume',''))+':'+str(r.get('pages',''))+
            '. DOI: '+str(r.get('doi',''))+'. PMID: '+r['pmid'])
def setup(d):
    s=d.sections[0];s.top_margin=Inches(.65);s.bottom_margin=Inches(.65)
    s.left_margin=Inches(.73);s.right_margin=Inches(.73)
    d.styles['Normal'].font.size=Pt(9)
    d.styles['Normal'].font.name='Aptos'
def create(results,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    evidence=Document();full=Document();setup(evidence);setup(full)
    evidence.add_heading('Integrative Mechanisms — Evidence Paragraphs',0)
    evidence.add_paragraph('FULL_TEXT = exact paragraph from article body in an official OA database. ABSTRACT_ONLY = PubMed abstract, not a full-text paragraph. NO_TEXT = text unavailable. Missing text has never been invented.')
    full.add_heading('Integrative Mechanisms — Open Access Full Text Bodies',0)
    full.add_paragraph('Contains only textual article body paragraphs made available by official Open Access APIs. PDF images, figures, and tables are excluded. Check the original article license before reuse.')
    log=[];nfull=0
    for idx,r in enumerate(results,1):
        name=r.get('title') or 'PMID '+r['pmid']
        sec=max(1,min(6,int(r.get('section') or 4)))
        evidence.add_heading(str(idx)+'. '+name,2)
        evidence.add_paragraph(cite(r))
        evidence.add_paragraph('PubMed: https://pubmed.ncbi.nlm.nih.gov/'+r['pmid']+'/ | PMCID '+r.get('pmcid','')+' | Subsection '+str(sec)+': '+HEADINGS[sec-1])
        evidence.add_paragraph('Evidence type: '+r.get('source_flag','NO_TEXT')+' | Source: '+r.get('oa_source',''))
        p=r.get('paragraph') or {}
        if p.get('text'):
            evidence.add_paragraph('Original section: '+p.get('section',''))
            evidence.add_paragraph(p['text'])
        else:evidence.add_paragraph('[No accessible evidence text was returned.]')
        if r.get('body'):
            nfull+=1;full.add_heading(str(nfull)+'. '+name,1)
            full.add_paragraph(cite(r))
            full.add_paragraph('https://pubmed.ncbi.nlm.nih.gov/'+r['pmid']+'/ | '+r.get('oa_source',''))
            previous=''
            for block in r['body']:
                heading=block.get('section') or ''
                if heading and heading!=previous:full.add_heading(heading,2);previous=heading
                full.add_paragraph(block['text'])
        log.append([r.get('rank',idx),r['pmid'],r.get('pmcid',''),r.get('source_flag',''),
                    len(r.get('body') or []),r.get('oa_source',''),name])
    evidence_file=out/'Integrative_Evidence_Paragraphs.docx'
    full_file=out/'Integrative_OA_Full_Texts.docx'
    evidence.save(evidence_file);full.save(full_file)
    stats_file=out/'Retrieval_Status.csv'
    with stats_file.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['rank','pmid','pmcid','source_type','fulltext_paragraphs','OA_source','article_title']);writer.writerows(log)
    report={'articles':len(results),'OA_fulltext_articles':nfull,
            'ABSTRACT_ONLY':sum(r.get('source_flag')=='ABSTRACT_ONLY' for r in results),
            'NO_TEXT':sum(r.get('source_flag')=='NO_TEXT' for r in results)}
    report_file=out/'Retrieval_Report.json'
    report_file.write_text(json.dumps(report,indent=2),encoding='utf8')
    archive=out/'Integrative_Word_Outputs.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in [evidence_file,full_file,stats_file,report_file]:z.write(f,f.name)
    print('FINISHED:',json.dumps(report),'ZIP:',archive,flush=True)
    try:
        from google.colab import files
        files.download(str(archive))
    except:print('Download from Colab Files pane:',archive,flush=True)


#!/usr/bin/env python3
"""Run all 1,112 article extractions with retry, cache, and Colab Word output."""
import argparse,csv,io,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
PREFIX='https://raw.githubusercontent.com/samadzadehartin-svg/test/main/integrative-research-2026/parts/'
def selected_ids(custom=None):
    if custom:
        data=Path(custom).read_text(encoding='utf-8-sig')
        if data.lstrip().startswith('pmid'):
            return [{'pmid':r['pmid'],'pmcid':r.get('pmcid',''),'section':int(r.get('section') or 4),'rank':int(r.get('rank') or i+1)}
                    for i,r in enumerate(csv.DictReader(io.StringIO(data),delimiter='\t'))]
        texts=[data]
    else:
        texts=[]
        for part in range(1,7):
            r=get(PREFIX+'selected_ids_'+format(part,'02d')+'.txt')
            if r is None:raise RuntimeError('GitHub manifest part '+str(part)+' unavailable. Try again or upload article_ids.tsv and set --manifest.')
            texts.append(r.text)
    found=[];seen=set()
    for data in texts:
        for pair in data.strip().replace('\n','').split(','):
            try:pmid,sec=pair.strip().split(':');sec=int(sec)
            except:continue
            if not pmid.isdigit() or not 1<=sec<=6 or pmid in seen:continue
            seen.add(pmid)
            found.append({'pmid':pmid,'section':sec,'rank':len(found)+1,'pmcid':''})
    if not custom and len(found)!=1112:raise RuntimeError('Expected 1112 IDs from GitHub, received '+str(len(found))+'. No extraction started.')
    return found
def main():
    a=argparse.ArgumentParser()
    a.add_argument('--manifest',default=None,help='Local TSV or comma-separated PMID:section file (optional)')
    a.add_argument('--out',default='/content/IntegrativeResearch')
    a.add_argument('--limit',type=int,default=0,help='Test a smaller initial batch; default ALL articles')
    a.add_argument('--workers',type=int,default=3)
    a.add_argument('--make-only',action='store_true')
    args=a.parse_args()
    items=selected_ids(args.manifest)
    if args.limit:items=items[:args.limit]
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    cache=out/'cache';cache.mkdir(exist_ok=True)
    print('Loaded',len(items),'selected unique articles; cache:',cache,flush=True)
    result={}
    if args.make_only:
        for x in items:
            f=cache/(x['pmid']+'.json')
            if f.exists():
                try:result[x['pmid']]=json.loads(f.read_text(encoding='utf8'))
                except:pass
    else:
        with ThreadPoolExecutor(max_workers=max(1,min(3,args.workers))) as executor:
            future={executor.submit(process,item,cache):item for item in items}
            for n,f in enumerate(as_completed(future),1):
                item=future[f]
                try:result[item['pmid']]=f.result()
                except Exception as exc:
                    print('WARN failed',item['pmid'],str(exc)[:140],flush=True)
                    result[item['pmid']]={**item,'title':'','authors':'','body':[],'paragraph':{'text':'','section':''},'source_flag':'NO_TEXT','oa_source':''}
                if n%25==0 or n==len(items):
                    print('Completed',n,'of',len(items),'| full texts:',sum(bool(x.get('body')) for x in result.values()),flush=True)
    ordered=[result[x['pmid']] for x in items if x['pmid'] in result]
    if not ordered:raise RuntimeError('No cached or retrieved records to write.')
    create(ordered,out)
if __name__=='__main__':main()
