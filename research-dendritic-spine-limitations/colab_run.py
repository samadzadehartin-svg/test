# -*- coding: utf-8 -*-
"""Google Colab collection of licensed OA full text for PubMed IDs from this GitHub folder.
Requires: pip install requests lxml python-docx tqdm
Full article body is retrieved only from Europe PMC OA XML; others get labeled abstracts.
"""
import argparse, base64, csv, gzip, json, re, time, zlib
from pathlib import Path
import requests
from lxml import etree
from docx import Document
from docx.shared import Pt
from tqdm.auto import tqdm

RAW="https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research-dendritic-spine-limitations/"
API="https://www.ebi.ac.uk/europepmc/webservices/rest/"
S=requests.Session()
S.headers.update({"User-Agent":"Academic dendritic-spine research collector/1.0","Accept-Encoding":"gzip, deflate"})
_LAST=[0.]
def get(url, params=None):
    for n in range(5):
        pause=max(0, _LAST[0]+0.46-time.monotonic())
        if pause: time.sleep(pause)
        _LAST[0]=time.monotonic()
        try:
            r=S.get(url,params=params,timeout=55)
            if r.status_code==200: return r
            if r.status_code in (403,404): return r
            if r.status_code not in (429,500,502,503,504): return r
            time.sleep(min(25,2**n))
        except requests.RequestException: time.sleep(min(25,2**n))
    return None

def ids():
    r=get(RAW+"selected_pmids_delta.b64")
    if r is None or r.status_code!=200: raise RuntimeError("GitHub PMID list unavailable")
    deltas=list(map(int,zlib.decompress(base64.b64decode(r.text.strip())).decode().split(",")))
    total=0; out=[]
    for d in deltas:
        total+=d; out.append(str(total))
    assert len(out)==1252 and len(set(out))==1252, "PMID catalog check failed"
    return out

def get_metadata(pmids):
    out={}
    for j in tqdm(range(0,len(pmids),25),desc="Europe PMC metadata"):
        group=pmids[j:j+25]
        q="("+" OR ".join("EXT_ID:"+p for p in group)+") AND SRC:MED"
        r=get(API+"search",{"query":q,"format":"json","resultType":"core","pageSize":100})
        if r is None or r.status_code!=200:continue
        for item in r.json().get("resultList",{}).get("result",[]):
            p=str(item.get("pmid") or item.get("id") or "")
            if p in group:out[p]=item
    for p in tqdm([p for p in pmids if p not in out],desc="Retry missing metadata"):
        r=get(API+"search",{"query":"EXT_ID:"+p+" AND SRC:MED","format":"json","resultType":"core","pageSize":1})
        if r is not None and r.status_code==200:
            hit=r.json().get("resultList",{}).get("result",[])
            if hit:out[p]=hit[0]
    return out

def text(el):
    return " ".join(" ".join(el.itertext()).split())
def parse_jats(xml):
    root=etree.fromstring(xml, parser=etree.XMLParser(no_network=True,resolve_entities=False))
    bodies=root.xpath('//*[local-name()="body"]')
    if not bodies:return [],""
    out=[]
    for p in bodies[0].xpath('.//*[local-name()="p"]'):
        if p.xpath('ancestor::*[local-name()="fig" or local-name()="table-wrap" or local-name()="ref-list" or local-name()="supplementary-material"]'):continue
        content=text(p)
        if len(content)<25:continue
        sec=p.xpath('ancestor::*[local-name()="sec"][1]/*[local-name()="title"]')
        heading=text(sec[0]) if sec else "Main text"
        out.append((heading,content))
    licenses=root.xpath('//*[local-name()="license"]')
    license_text="; ".join(text(x)[:200] for x in licenses)
    return out,license_text

def best_para(paras,abstract):
    if not paras:return abstract
    w={'dendritic spine':10,'synaptic density':8,'depress':5,'suicid':7,
       'limitation':12,'future':10,'animal':3,'human':3,'confound':9,
       'heterogen':8,'causal':9,'imaging':5,'postmortem':6}
    def score(p):
        h,t=p;low=t.lower();res=sum(v*low.count(k) for k,v in w.items())
        if re.search("limit|future|conclu|discussion",h,re.I):res+=25
        return res
    return max(paras,key=score)[1]

def safe(s):
    return re.sub("<[^>]+>"," ",s or "").strip()

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--output",default="/content/limitations_fulltext" if Path("/content").exists() else "limitations_fulltext")
    arg.add_argument("--limit",type=int,default=0,help="Test only; 0=ALL 1252")
    args=arg.parse_args()
    folder=Path(args.output);folder.mkdir(parents=True,exist_ok=True)
    cache=folder/"cache";cache.mkdir(exist_ok=True)
    pmids=ids()
    if args.limit:pmids=pmids[:args.limit]
    print("Selected unique PMIDs:",len(pmids))
    metafile=folder/"metadata.json"
    if metafile.exists():
        metadata=json.loads(metafile.read_text("utf-8"))
    else:
        metadata={}
    missing=[p for p in pmids if p not in metadata]
    if missing:
        metadata.update(get_metadata(missing))
        metafile.write_text(json.dumps(metadata,ensure_ascii=False),"utf-8")
    statuses=[]
    for p in tqdm(pmids,desc="Licensed full texts"):
        f=cache/(p+".json.gz")
        if f.exists():
            with gzip.open(f,"rt",encoding="utf-8") as h:continue_record=json.load(h)
        else:
            m=metadata.get(p,{})
            abstract=safe(m.get("abstractText"))
            continue_record={"pmid":p,"status":"ABSTRACT_ONLY",
                "text":[],"evidence":abstract,"license":"","error":""}
            pmcid=m.get("pmcid") or ""
            if pmcid.startswith("PMC") and str(m.get("isOpenAccess","")).upper()=="Y":
                r=get(API+pmcid+"/fullTextXML")
                if r is not None and r.status_code==200:
                    try:
                        pars,license_text=parse_jats(r.content)
                        if pars:
                            continue_record.update(status="FULLTEXT_OA",
                              text=pars,evidence=best_para(pars,abstract),license=license_text)
                    except Exception as e:continue_record["error"]=str(e)[:200]
                else:continue_record["error"]="OA XML endpoint unavailable"
            elif pmcid:
                continue_record["error"]="PMCID exists, but OA reuse flag is not Y"
            else:continue_record["error"]="No PMCID / no legal OA XML"
            with gzip.open(f,"wt",encoding="utf-8") as h:json.dump(continue_record,h,ensure_ascii=False)
        statuses.append((p,continue_record["status"],continue_record["error"]))
    full=Document();evidence=Document()
    for d,title in ((full,"Open-access full-text articles"),(evidence,"Verbatim selected paragraphs")):
        d.add_heading(title+" — Dendritic Spine Limitations",level=0)
        d.styles["Normal"].font.name="Calibri"
        d.styles["Normal"].font.size=Pt(9)
    for j,p in enumerate(tqdm(pmids,desc="Building Word files"),1):
        m=metadata.get(p,{})
        with gzip.open(cache/(p+".json.gz"),"rt",encoding="utf-8") as h:o=json.load(h)
        ji=m.get("journalInfo") or {}
        jo=ji.get("journal") or {}
        citation=(f'{m.get("authorString","")}. {safe(m.get("title"))}. '
                  f'{m.get("journalTitle") or jo.get("title","")}. {m.get("pubYear","")};'
                  f'{ji.get("volume","")}:{m.get("pageInfo","")}. DOI: {m.get("doi","")}.')
        title=f"{j}. {safe(m.get('title')) or ('PMID '+p)}"
        bib=citation+f"\nPMID: {p} | PMCID: {m.get('pmcid','N/A')}\nhttps://pubmed.ncbi.nlm.nih.gov/{p}/"
        for doc in (full,evidence):
            doc.add_heading(title,level=1)
            doc.add_paragraph(bib)
            doc.add_paragraph(f"Text status: {o['status']} | License: {o['license'] or 'consult original article'}")
        evidence.add_paragraph(o.get("evidence") or "No extractable text")
        if o["status"]=="FULLTEXT_OA":
            last=""
            for heading,para in o["text"]:
                if heading!=last:full.add_heading(heading,level=2);last=heading
                full.add_paragraph(para)
        else:
            full.add_heading("Abstract only — full text not legally available through API",level=2)
            full.add_paragraph(o.get("evidence") or "No abstract available")
    for doc,name in ((full,"Limitations_OA_FullText.docx"),
                     (evidence,"Limitations_Exact_Evidence_Paragraphs.docx")):
        dest=folder/name;doc.save(dest);print("Saved:",dest)
    with (folder/"retrieval_status.csv").open("w",newline="",encoding="utf-8-sig") as h:
        w=csv.writer(h);w.writerow(["PMID","Status","Reason"]);w.writerows(statuses)
    print("FULLTEXT_OA:",sum(s[1]=="FULLTEXT_OA" for s in statuses),
          "| ABSTRACT_ONLY:",sum(s[1]=="ABSTRACT_ONLY" for s in statuses))
    try:
        from google.colab import files
        files.download(str(folder/"Limitations_Exact_Evidence_Paragraphs.docx"))
        files.download(str(folder/"Limitations_OA_FullText.docx"))
    except ImportError:pass

if __name__=="__main__":main()
