#!/usr/bin/env python3
# Colab / Python 3.10+: download the user-selected 1211 PubMed records from GitHub,
# retrieve public bibliographic data, then open-access full text from Europe PMC.
# Produce source-grounded evidence paragraphs and complete OA full texts in Word.
# NO paywall circumvention, no invented paragraphs.
import sys,os,re,csv,json,time,html,threading,random,zipfile
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
try:
 import requests
 from lxml import etree
 from docx import Document
 from docx.shared import Pt,Cm,RGBColor
except ImportError:
 import subprocess
 subprocess.check_call([sys.executable,'-m','pip','-q','install','requests>=2.31','lxml>=5','python-docx>=1.1'])
 import requests
 from lxml import etree
 from docx import Document
 from docx.shared import Pt,Cm,RGBColor

# Public GitHub repository with selected research PubMed IDs and metadata.
ROOT='https://raw.githubusercontent.com/samadzadehartin-svg/test/main/limitations_2026'
MANIFEST_URL=ROOT+'/ranked_articles.csv'
DEST=Path('/content/limitations_oa_results' if Path('/content').exists() else 'limitations_oa_results')
DEST.mkdir(parents=True,exist_ok=True)
CACHE=DEST/'verified_records.jsonl'
MAX_WORKERS=3  # respectful to literature API; adjust to 1 if rate limited.
TIMEOUT=30
SAVE_ABSTRACT_FOR_NONOA=True
INCLUDE_COMPLETE_OA_TEXT=True
TERMS=[
 r'dendritic spin',r'synap',r'depress',r'suicid',r'limit',r'confound',r'heterogen',
 r'causal',r'correlat',r'postmortem',r'live human',r'in vivo',r'PET',r'SV2A',
 r'cell.type',r'brain region',r'antidepressant',r'comorbid',r'future',r'clinical',
 r'animal model',r'preclinical',r'longitudinal',r'translat',r'variab',r'medicat',r'optic'
]
SES=requests.Session()
SES.headers.update({'User-Agent':'AcademicLiteratureCollector/1.0 (literature review; respectful access)','Accept':'application/json,application/xml,text/xml,text/plain;q=0.8'})

def get(url,params=None):
 for attempt in range(6):
  try:
   res=SES.get(url,params=params,timeout=TIMEOUT)
   if res.status_code in (429,500,502,503,504):
    delay=min(45,2**attempt+random.random()*2)
    print('Retry',res.status_code,url.split('/')[-1],round(delay,1),flush=True)
    time.sleep(delay);continue
   res.raise_for_status();return res
  except (requests.Timeout,requests.ConnectionError):
   if attempt==5:raise
   time.sleep(min(32,2**attempt)+random.random())
 raise RuntimeError('Retry limit exceeded: '+url)

def load_manifest():
 try:
  resp=get(MANIFEST_URL)
 except Exception as exc:
  raise RuntimeError('Cannot download GitHub manifest: '+str(exc)) from exc
 path=DEST/'ranked_articles.csv';path.write_bytes(resp.content)
 # UTF-8 with or without BOM
 with path.open(encoding='utf-8-sig',newline='') as fp:
  rows=list(csv.DictReader(fp))
 ids=[r.get('pmid','').strip() for r in rows]
 rows=[r for r in rows if re.fullmatch(r'\d{5,10}',r.get('pmid',''))]
 print('Manifest received:',len(rows),'unique',len(set(ids)),flush=True)
 if not rows:raise RuntimeError('GitHub manifest is empty or improperly formatted.')
 return rows

def batched(items,n):
 for k in range(0,len(items),n):yield items[k:k+n]

def europepmc_meta(rows):
 endpoint='https://www.ebi.ac.uk/europepmc/webservices/rest/search'
 output={}
 # Query 25 PMIDs per call. Ensures no 1200 separate metadata requests.
 for c,ch in enumerate(batched(rows,25),1):
  ids=[r['pmid'] for r in ch]
  query='('+ ' OR '.join('EXT_ID:'+p for p in ids) +') AND SRC:MED'
  try:
   js=get(endpoint,params={'query':query,'format':'json','resultType':'core','pageSize':100}).json()
   for entry in js.get('resultList',{}).get('result',[]):
    key=str(entry.get('pmid') or entry.get('id') or '')
    if key in ids:output[key]=entry
  except Exception as exc:print('Metadata batch failure:',c,str(exc)[:120],flush=True)
  if c%10==0:print('Metadata:',len(output),'/',len(rows),flush=True)
  time.sleep(.23)
 # For unusual records omitted by multi-ID lookup, request individually.
 miss=[r['pmid'] for r in rows if r['pmid'] not in output]
 for i,pid in enumerate(miss,1):
  try:
   js=get(endpoint,params={'query':'EXT_ID:'+pid,'format':'json','resultType':'core','pageSize':3}).json()
   results=js.get('resultList',{}).get('result',[])
   choose=next((x for x in results if str(x.get('pmid'))==pid),None)
   if choose:output[pid]=choose
  except Exception as exc:print('Metadata unavailable:',pid,str(exc)[:100],flush=True)
  if i%10==0:print('Checking individual records:',i,'/',len(miss),flush=True)
  time.sleep(.25)
 return output

def normalized_text(node):
 # Includes <italic>/<xref>, preserving original paragraph word order.
 t=''.join(node.itertext())
 return re.sub(r'\s+',' ',html.unescape(t)).strip()

def fulltext_paragraphs(xml_text):
 parser=etree.XMLParser(recover=True,remove_comments=True,resolve_entities=False,no_network=True,huge_tree=True)
 root=etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text,str) else xml_text,parser)
 candidates=root.xpath('//*[local-name()="body"]//*[local-name()="p"]')
 paras=[];seen=set()
 for p in candidates:
  if any(etree.QName(ancestor).localname in ('table-wrap','fig','supplementary-material','ref-list') for ancestor in p.iterancestors()):continue
  content=normalized_text(p)
  if len(content)<30 or content in seen:continue
  seen.add(content);paras.append(content)
 return paras

def score_paragraph(text,section=''):
 low=text.lower();hits=0
 for p in TERMS:
  if re.search(p,low,re.I):hits+=1
 if re.search(r'limitation|challenge|confounding|causality|postmortem|heterogeneity|cross.sectional|future studies|human versus',low):hits+=5
 if 'Imaging' in section and re.search(r'imag|microscop|sv2a|pet',low):hits+=5
 if 'Medication' in section and re.search(r'medicat|antidepress|ketamin|comorbid',low):hits+=5
 if 'Animal' in section and re.search(r'preclinical|animal|human|species',low):hits+=5
 if 'Correlation' in section and re.search(r'caus|associat|manipulat|longitudinal',low):hits+=5
 if len(text)>3200:hits-=4
 if len(text)<85:hits-=2
 return hits

def abstract_text(meta):
 v=meta.get('abstractText','') or ''
 return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',html.unescape(v))).strip()

def citation(row,meta):
 author=meta.get('authorString') or row.get('authors') or 'Authors not listed'
 ji=meta.get('journalInfo') or {}
 jo=ji.get('journal') or {}
 journal=jo.get('title') or meta.get('journalTitle') or row.get('journal') or ''
 year=meta.get('pubYear') or row.get('year') or ''
 vol=ji.get('journalIssueId') or ji.get('journalIssueId',row.get('volume',''))
 vol=row.get('volume') or str(vol or '')
 issue=row.get('issue') or ''
 pages=meta.get('pageInfo') or row.get('pages') or ''
 title=meta.get('title') or row.get('title') or ''
 doi=meta.get('doi') or row.get('doi') or ''
 return f'{author}. {title} {journal}. {year};{vol}'+(f'({issue})' if issue else '')+(f':{pages}' if pages else '')+f'. DOI: {doi}. PMID: {row["pmid"]}.'

def fetch_one(row,metadata):
 pid=row['pmid'];meta=metadata.get(pid,{})
 oa=meta.get('isOpenAccess')=='Y' and meta.get('inEPMC')=='Y' and bool(meta.get('pmcid'))
 fulltext=[];status='ABSTRACT_ONLY';error=''
 if oa:
  pmcid=meta['pmcid']
  try:
   result=get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
   fulltext=fulltext_paragraphs(result.content)
   if fulltext:status='OPEN_ACCESS_FULLTEXT'
   else:status='OA_NO_BODY_PARAGRAPH'
  except Exception as exc:status='OA_DOWNLOAD_FAILED';error=str(exc)[:350]
 abstract=abstract_text(meta) or row.get('evidence_from_uploaded_abstract') or ''
 evidence_source='FULL_TEXT' if fulltext else 'ABSTRACT'
 if fulltext:
  eligible=[p for p in fulltext if 80<=len(p)<=6000] or fulltext
  evidence=max(eligible,key=lambda x:score_paragraph(x,row.get('primary_topic','')))
 else:
  candidates=re.split(r'(?<=[.!?])\s+(?=[A-Z])',abstract)
  evidence=max(candidates,key=lambda x:score_paragraph(x,row.get('primary_topic',''))) if candidates else ''
 if not evidence:evidence='[No verifiable evidence paragraph retrieved]'
 return {'pmid':pid,'rank':row.get('global_rank',''),'priority':row.get('priority',''),
         'citation':citation(row,meta),'title':meta.get('title') or row.get('title',''),
         'doi':meta.get('doi') or row.get('doi',''),'pmcid':meta.get('pmcid') or row.get('pmcid',''),
         'isOpenAccess':meta.get('isOpenAccess'),'license':meta.get('license') or '',
         'pubmed_url':'https://pubmed.ncbi.nlm.nih.gov/'+pid+'/',
         'topic':row.get('primary_topic',''),'source_files':row.get('source_files',''),
         'status':status,'error':error,'evidence_source':evidence_source,
         'evidence':evidence,'abstract':abstract,'fulltext_paragraphs':fulltext if INCLUDE_COMPLETE_OA_TEXT else []}

def new_doc(title):
 d=Document();section=d.sections[0];section.left_margin=Cm(2);section.right_margin=Cm(2)
 section.top_margin=Cm(1.8);section.bottom_margin=Cm(1.6)
 st=d.styles['Normal'];st.font.name='Calibri';st.font.size=Pt(9)
 st.paragraph_format.space_after=Pt(5)
 d.add_heading(title,0);return d

def write_evidence(records):
 doc=new_doc('Limitations and Future Research Directions — Verified Evidence')
 doc.add_paragraph('Source provenance: Europe PMC open-access full text when available. Otherwise only the indexed abstract. Text quoted verbatim from retrieved source, not generated.')
 doc.add_paragraph('Important: OPEN_ACCESS_FULLTEXT means the selected paragraph comes from an article body; ABSTRACT_ONLY never implies full article retrieval.')
 for r in records:
  q=doc.add_paragraph();q.paragraph_format.keep_with_next=True
  rr=q.add_run(f'[{r["rank"]}] {r["title"]}');rr.bold=True;rr.font.size=Pt(10)
  doc.add_paragraph(r['citation'])
  doc.add_paragraph(f'Priority: {r["priority"]} | Subsection: {r["topic"]} | Status: {r["status"]} | Evidence: {r["evidence_source"]}')
  doc.add_paragraph(r['evidence'])
  doc.add_paragraph(r['pubmed_url'])
 f=DEST/'Evidence_Paragraphs_ALL.docx';doc.save(f);print('Saved',f,flush=True)

def write_fulltext(records):
 if not INCLUDE_COMPLETE_OA_TEXT:return
 matches=[r for r in records if r['fulltext_paragraphs']]
 if not matches:
  print('No open-access fulltext was retrieved; full-text Word not created.',flush=True);return
 d=new_doc('Limitations and Future Research Directions — Complete Open Access Article Texts')
 d.add_paragraph('Only articles explicitly identified as OPEN ACCESS by Europe PMC are included. Other records appear in the evidence/availability report instead.')
 for i,r in enumerate(matches,1):
  if i>1:d.add_page_break()
  d.add_heading(f'[{r["rank"]}] {r["title"]}',level=2)
  d.add_paragraph(r['citation']);d.add_paragraph(f'PMCID: {r["pmcid"]} | License: {r["license"]} | {r["pubmed_url"]}')
  for p in r['fulltext_paragraphs']:d.add_paragraph(p)
  if i%80==0:
   filename=DEST/'FullTexts_OpenAccess_ALL.docx'
   d.save(filename)
   print('Saved checkpoint of fulltext Word:',i,'/',len(matches),flush=True)
 filename=DEST/'FullTexts_OpenAccess_ALL.docx';d.save(filename)
 print('Saved',filename,'for',len(matches),'open-access articles',flush=True)

def main():
 rows=load_manifest();existing={}
 if CACHE.exists():
  for ln in CACHE.read_text(encoding='utf-8').splitlines():
   try:
    obj=json.loads(ln);existing[obj['pmid']]=obj
   except Exception:pass
 print('Resuming from cache:',len(existing),flush=True)
 todo=[r for r in rows if r['pmid'] not in existing or existing[r['pmid']].get('status')=='OA_DOWNLOAD_FAILED']
 print('Records needing extraction:',len(todo),flush=True)
 metadata=europepmc_meta(todo) if todo else {}
 print('Found public metadata:',len(metadata),'/',len(todo),flush=True)
 lock=threading.Lock()
 with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool, CACHE.open('a',encoding='utf-8') as fp:
  futures={pool.submit(fetch_one,row,metadata):row for row in todo}
  for n,f in enumerate(as_completed(futures),1):
   row=futures[f]
   try:result=f.result()
   except Exception as exc:
    result=fetch_one(row,{})
    result['status']='FETCH_FAILED';result['error']=str(exc)[:300]
   existing[row['pmid']]=result
   fp.write(json.dumps(result,ensure_ascii=False)+'\n');fp.flush()
   if n%20==0 or n==len(todo):
    counts={key:sum(r['status']==key for r in existing.values()) for key in ['OPEN_ACCESS_FULLTEXT','ABSTRACT_ONLY','OA_DOWNLOAD_FAILED','FETCH_FAILED']}
    print('Processed',n,'/',len(todo),'|',counts,flush=True)
 ordered=[existing[r['pmid']] for r in rows if r['pmid'] in existing]
 print('Writing Word and availability CSV...',flush=True)
 with (DEST/'Availability_Report.csv').open('w',encoding='utf-8-sig',newline='') as fp:
  fields=['rank','pmid','title','priority','topic','status','pmcid','doi','isOpenAccess','license','evidence_source','pubmed_url','error']
  w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k,'') for k in fields} for r in ordered)
 write_evidence(ordered)
 write_fulltext(ordered)
 with zipfile.ZipFile(DEST/'Results_Word_and_CSV.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for fname in ['Evidence_Paragraphs_ALL.docx','FullTexts_OpenAccess_ALL.docx','Availability_Report.csv']:
   f=DEST/fname
   if f.exists():z.write(f,f.name)
 print('FINISHED: Outputs in',DEST,flush=True)
 try:
  from google.colab import files
  files.download(str(DEST/'Results_Word_and_CSV.zip'))
 except ImportError:pass

if __name__=='__main__':main()