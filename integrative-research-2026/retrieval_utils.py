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
