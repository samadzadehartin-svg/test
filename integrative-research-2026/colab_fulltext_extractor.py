#!/usr/bin/env python3
"""Run all 1,112 article extractions with retry, cache, and Colab Word output."""
import argparse,csv,io,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from retrieval_utils import get,process
from make_docx import create
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
