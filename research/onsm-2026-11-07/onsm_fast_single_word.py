#!/usr/bin/env python3
# ONSM FAST single Word. Open-access retrieval only; 536 occurrences, 224 unique PMIDs.
import sys,re,json,zlib,base64,argparse,threading,concurrent.futures as cf
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote,urlparse
import requests
from bs4 import BeautifulSoup as BS
from docx import Document
from docx.shared import Pt,Cm
THREAD=threading.local()
E='https://www.ebi.ac.uk/europepmc/webservices/rest'
def sess():
 if not hasattr(THREAD,'s'):
  s=requests.Session();s.headers.update({'User-Agent':'ONSM-academic-OA-retrieval/2.1','Accept':'*/*'});THREAD.s=s
 return THREAD.s
def clean(s):return re.sub(r'\s+',' ',str(s or '')).strip()
def safe(u):
 try:
  p=urlparse(u);h=p.hostname or ''
  return p.scheme=='https' and h not in ('localhost','127.0.0.1','169.254.169.254') and not h.endswith(('.local','.internal')) and not re.fullmatch(r'[0-9.]+',h)
 except:return False
def readurl(url,mb=12,timeout=(4,10)):
 if not safe(url):raise ValueError('Unsafe URL')
 with sess().get(url,stream=True,timeout=timeout) as r:
  r.raise_for_status()
  if not safe(r.url):raise ValueError('Unsafe redirect')
  if int(r.headers.get('content-length',0) or 0)>mb*1000000:raise ValueError('Oversized')
  parts=[];total=0
  for chunk in r.iter_content(65536):
   total+=len(chunk)
   if total>mb*1000000:raise ValueError('Oversized')
   parts.append(chunk)
  return b''.join(parts)
def getjson(u):return json.loads(readurl(u,mb=2).decode('utf-8-sig'))
def getlist(path):
 s=BS(Path(path).read_text(encoding='utf8'),'html.parser')
 t=s.find('script',id='dataset')
 if not t:raise ValueError('No embedded ONSM dataset')
 d=json.loads(t.string or t.get_text())
 if isinstance(d,dict) and 'packed_zlib64' in d:d=json.loads(zlib.decompress(base64.b64decode(d['packed_zlib64'])))
 if isinstance(d,list):return d
 if 'records' in d:return d['records']
 if 'unique_pmids' in d:
  return [{'pmid':str(d['unique_pmids'][i]),'title':'','doi':'','authors':[],'year':'','abstract':''} for i in d['occurrence_indices']]
 raise ValueError('Bad manifest')
def metadata(pmid):
 q=quote('EXT_ID:'+pmid+' AND SRC:MED',safe='')
 d=getjson(E+'/search?query='+q+'&format=json&resultType=core&pageSize=1')
 a=d.get('resultList',{}).get('result',[])
 return a[0] if a else {}
def jats(data):
 body=BS(data,'xml').find('body')
 if not body:return ''
 parts=[]
 for el in body.find_all(['sec','p','table-wrap']):
  if el.name=='sec':
   heading=el.find('title',recursive=False)
   if heading:parts.append('\n'+clean(heading.get_text(' ',strip=True))+'\n')
  elif el.name=='p':
   if not el.find_parent('table-wrap'):parts.append(clean(el.get_text(' ',strip=True)))
  else:
   label=el.find('label');capt=el.find('caption')
   cellrows=[' | '.join(clean(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'])) for row in el.find_all('tr')]
   parts.append('\n'.join([clean(label.get_text(' ',strip=True)) if label else '',clean(capt.get_text(' ',strip=True)) if capt else '',*cellrows]))
 return '\n\n'.join(x for x in parts if x)
def valid(text,abstract):return len(clean(text))>=950 and len(text.split())>=130 and len(clean(text))>len(clean(abstract))*1.1
def pdftext(binary):
 if not binary.startswith(b'%PDF'):return ''
 import fitz
 with fitz.open(stream=binary,filetype='pdf') as pdf:
  if len(pdf)<2 or len(pdf)>250:return ''
  return '\n\n'.join(p.get_text(sort=True) for p in pdf)
def identity(txt,a):
 head=clean(txt[:15000]).lower();doi=clean(a.get('doi')).lower()
 if doi and doi in head:return True
 words=set(re.findall(r'[a-z]{4,}',clean(a.get('title')).lower()))-{'this','study','with','from','the','and','using'}
 if len(words)<3:return False
 return len(words.intersection(set(re.findall(r'[a-z]{4,}',head))))>=max(3,int(len(words)*0.65))
def oapdfs(doi):
 if not doi:return []
 try:
  d=getjson('https://api.openalex.org/works/'+quote('https://doi.org/'+doi,safe=''))
  urls=[]
  for x in [d.get('best_oa_location')]+(d.get('locations') or []):
   if x and x.get('is_oa') and safe(x.get('pdf_url') or '') and x['pdf_url'] not in urls:urls.append(x['pdf_url'])
   if len(urls)>=2:break
  return urls
 except:return []
def article(row):
 a=dict(row);a['pmid']=str(a.get('pmid') or '');a.setdefault('abstract','');a.setdefault('authors',[])
 a.update({'status':'ABSTRACT','content':'','source':'','source_url':''})
 try:
  try:info=metadata(a['pmid']) if a['pmid'] else {}
  except:info={}
  for k,v in [('title',info.get('title')),('doi',info.get('doi')),('year',info.get('pubYear')),('pubdate',info.get('firstPublicationDate')),('journal',info.get('journalTitle')),('authors',info.get('authorString'))]:
   if not a.get(k):a[k]=v or ''
  if not a['abstract']:a['abstract']=BS(info.get('abstractText') or '','html.parser').get_text(' ',strip=True)
  pmc=clean(info.get('pmcid'))
  if pmc and (info.get('isOpenAccess')=='Y' or info.get('inEPMC')=='Y'):
   try:
    u=E+'/'+quote(pmc)+'/fullTextXML';txt=jats(readurl(u,mb=12))
    if valid(txt,a['abstract']):
     a.update({'status':'FULL TEXT','content':txt,'source':'Europe PMC full-text XML','source_url':u});return a
   except:pass
  for u in oapdfs(clean(a.get('doi'))):
   try:
    txt=pdftext(readurl(u,mb=18,timeout=(4,12)))
    if valid(txt,a['abstract']) and identity(txt,a):
     a.update({'status':'FULL TEXT','content':txt,'source':'OpenAlex OA PDF','source_url':u});return a
   except:pass
 except:pass
 return a
def report(rows,counts,path):
 doc=Document();sect=doc.sections[0];sect.top_margin=Cm(1.8);sect.bottom_margin=Cm(1.8)
 sect.left_margin=Cm(2);sect.right_margin=Cm(2)
 doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(10)
 doc.add_heading('ONSM | Full Text or Abstract',0)
 doc.add_paragraph('Research articles in original input order. Available open-access full texts or, if unavailable, abstracts. Each unique PMID appears once; duplicate occurrences are counted.')
 doc.add_paragraph(f'Unique articles: {len(rows)} | Input occurrences: {sum(counts.values())}')
 for i,(key,a) in enumerate(rows.items(),1):
  doc.add_heading(str(i)+'. '+(a.get('title') or 'Untitled record'),2)
  author=a.get('authors') or ''
  if isinstance(author,list):author='; '.join(map(str,author))
  fields=[('Authors',author),('Journal',a.get('journal')),('Year',a.get('year')),('Publication date',a.get('pubdate')),('DOI',a.get('doi')),('PMID',a.get('pmid')),('PubMed','https://pubmed.ncbi.nlm.nih.gov/'+str(a.get('pmid') or '')+'/'),('Status',a.get('status')),('Retrieved from',a.get('source')),('Source URL',a.get('source_url')),('Occurrences in source lists',counts.get(key,1))]
  for title,value in fields:
   if value:
    p=doc.add_paragraph();p.add_run(title+': ').bold=True;p.add_run(str(value))
  full=a.get('status')=='FULL TEXT';doc.add_heading('FULL TEXT' if full else 'ABSTRACT ONLY — FULL TEXT NOT RETRIEVED',3)
  txt=a.get('content') if full else a.get('abstract')
  txt=txt or '[Abstract not available]'
  for para in re.split(r'\n\s*\n',txt):
   if para.strip():
    for j in range(0,len(para),5500):doc.add_paragraph(para[j:j+5500])
  if i<len(rows):doc.add_page_break()
 doc.save(path)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--html',default='ONSM_All_536_Records.html')
 parser.add_argument('--out',default='ONSM_FullText_or_Abstract.docx')
 parser.add_argument('--workers',type=int,default=10);parser.add_argument('--limit',type=int,default=0)
 args=parser.parse_args();data=getlist(args.html);unique=OrderedDict();counts={}
 for i,row in enumerate(data):
  k=str(row.get('pmid') or row.get('doi') or 'row'+str(i))
  unique.setdefault(k,row);counts[k]=counts.get(k,0)+1
 if args.limit:unique=OrderedDict(list(unique.items())[:args.limit])
 folder=Path('ONSM_fast_cache');folder.mkdir(exist_ok=True)
 found={};pending={}
 for key,row in unique.items():
  p=folder/(re.sub(r'[^a-zA-Z0-9_-]','_',key)+'.json')
  try:
   obj=json.loads(p.read_text(encoding='utf8'))
   if str(obj.get('pmid'))==str(row.get('pmid')):found[key]=obj;continue
  except:pass
  pending[key]=(row,p)
 print(f'Input {len(data)} | Unique {len(unique)} | Cached {len(found)} | Searching {len(pending)}',flush=True)
 with cf.ThreadPoolExecutor(max_workers=max(1,min(12,args.workers))) as pool:
  tasks={pool.submit(article,row):(key,p) for key,(row,p) in pending.items()}
  for n,f in enumerate(cf.as_completed(tasks),1):
   key,p=tasks[f]
   try:result=f.result()
   except:result=dict(unique[key],status='ABSTRACT',content='',source='',source_url='')
   found[key]=result
   try:p.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
   except:pass
   if n%10==0 or n==len(tasks):
    print(f'Completed {len(found)}/{len(unique)} | Full texts {sum(x.get("status")=="FULL TEXT" for x in found.values())}',flush=True)
 report(OrderedDict((key,found[key]) for key in unique),counts,args.out)
 print('Saved',args.out,flush=True)
if __name__=='__main__':main()
