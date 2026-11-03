#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect licensed Open Access article body text from Europe PMC for the user's
679 PubMed records; preserve one copy per PMID. Run in Google Colab or Python."""
import csv, io, os, re, json, time, pathlib, zipfile
from collections import OrderedDict, Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree, html
from docx import Document
from docx.shared import Pt

ROOT="https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/nutrition_gut_brain_2026"
DEST=pathlib.Path("/content/Nutrition_GutBrain_Results" if pathlib.Path("/content").exists() else "Nutrition_GutBrain_Results")
CACHE=DEST/"cache"
DEST.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True)
RESULT=DEST/"Nutritional_FullText_Collected.docx"
REPORT=DEST/"retrieval_status.csv"
TOPICS=["Dietary patterns/synaptic plasticity","High-fat/sugar/Western diets",
"Omega-3 and micronutrients","Tryptophan/kynurenine pathway",
"Gut microbiota/short-chain fatty acids","Probiotics/prebiotics/psychobiotics",
"Alcohol/nicotine/cannabis/other substances"]
KEYWORDS=[
"diet dietary fasting nutrition polyphenol synaptic plasticity",
"high-fat sugar fructose obesity western hippocampus",
"omega-3 docosahexaenoic acid dha epa folate vitamin zinc magnesium",
"tryptophan kynurenine quinolinic indoleamine serotonin ido",
"microbiota gut-brain butyrate scfa microbiome neuroinflammation",
"probiotic prebiotic psychobiotic lactobacillus bifidobacterium",
"alcohol ethanol nicotine marijuana cannabis cannabinoid cocaine opioid morphine"
]
S=requests.Session()
S.headers.update({"User-Agent":"AcademicResearchEvidenceCollector/1.0 (Europe PMC official API)"})
S.mount("https://",HTTPAdapter(max_retries=Retry(total=4,backoff_factor=1.0,
 status_forcelist=[429,500,502,503,504],allowed_methods=["GET"],
 respect_retry_after_header=True)))
previous=0
def request(url,params=None):
    global previous
    if time.monotonic()-previous<0.45:time.sleep(0.45-(time.monotonic()-previous))
    previous=time.monotonic()
    try:
        r=S.get(url,params=params,timeout=(12,55))
        if r.status_code in (400,403,404,410):return None
        r.raise_for_status();return r
    except requests.RequestException as e:
        print("Network error; skipping:",str(e)[:140]);return None

def clean(s):return " ".join((s or "").replace("\xa0"," ").split())
def csv_from_github(name):
    r=request(ROOT+"/"+name)
    if r is None:raise RuntimeError("Could not fetch "+name+" from GitHub")
    return list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
def licence(root):
    vals=root.xpath("//*[local-name()='license']")
    text=" ".join(clean(" ".join(x.itertext())) for x in vals)
    links=" ".join(x.attrib.get("{http://www.w3.org/1999/xlink}href","") for x in vals)
    combined=(text+" "+links).lower()
    cc=any(t in combined for t in ["creativecommons.org/licenses/","creativecommons.org/publicdomain",
         "creative commons attribution","creativecommons attribution","cc0"])
    nd=any(t in combined for t in ["/by-nd/","/by-nc-nd/","no derivatives","no-derivatives"])
    return clean((text+" "+links)[:750]), bool(cc and not nd)
def parse_xml(data):
    try:root=etree.fromstring(data,parser=etree.XMLParser(resolve_entities=False,no_network=True))
    except etree.XMLSyntaxError:return [],"",False
    lic,ok=licence(root)
    bodies=root.xpath("//*[local-name()='body']")
    if not bodies:return [],lic,ok
    parts=[]
    for n in bodies[0].iter():
        if not isinstance(n.tag,str):continue
        kind=etree.QName(n).localname
        if kind not in ("title","p"):continue
        if any(etree.QName(a).localname in ("table-wrap","fig","ref-list","fn-group","boxed-text")
               for a in n.iterancestors() if isinstance(a.tag,str)):continue
        t=clean(" ".join(n.itertext()))
        if kind=="title" and len(t)>8:parts.append(("heading",t))
        elif kind=="p" and len(t)>40:parts.append(("paragraph",t))
    return parts,lic,ok
def evidence(parts,topic):
    words=KEYWORDS[topic-1].split() if 1<=topic<=7 else ["depression","synaptic","brain","gut"]
    anchors=["depression","depressive","suicid","synaptic","dendritic","spine","plasticity","bdnf","hippocamp"]
    picks=[]
    for kind,text in parts:
        if kind!="paragraph" or len(text)<150 or len(text)>4000:continue
        s=text.lower()
        score=sum(5 for w in words if w in s)+sum(4 for w in anchors if w in s)
        score+=2 if 300<=len(text)<=1500 else 0
        picks.append((score,text))
    return max(picks,key=lambda t:t[0])[1] if picks else ""
def fetch(pmid,topic):
    base="https://www.ebi.ac.uk/europepmc/webservices/rest"
    r=request(base+"/search",{"query":"EXT_ID:"+pmid+" AND SRC:MED",
        "format":"json","resultType":"core","pageSize":1})
    if r is None:return dict(pmid=pmid,status="metadata_unavailable",title="Metadata unavailable",body=[])
    try:entries=r.json().get("resultList",{}).get("result",[])
    except (ValueError,TypeError):entries=[]
    if not entries:return dict(pmid=pmid,status="metadata_not_found",title="Not found",body=[])
    z=entries[0]
    def flatten(x):
        try:return clean(html.fromstring("<div>"+x+"</div>").text_content())
        except Exception:return clean(x)
    d=dict(pmid=pmid,topic=topic,title=flatten(z.get("title","")),
        authors=z.get("authorString",""),journal=z.get("journalTitle",""),
        year=z.get("pubYear",""),doi=z.get("doi",""),pmcid=z.get("pmcid",""),
        abstract=flatten(z.get("abstractText","")),isOpenAccess=z.get("isOpenAccess","N"),
        license="",body=[],selected_paragraph="",status="abstract_only")
    if d["pmcid"] and d["isOpenAccess"]=="Y":
        link=base+"/"+d["pmcid"]+"/fullTextXML"
        f=request(link)
        if f is None:d["status"]="oa_fulltext_xml_not_available"
        else:
            paragraphs,lic,allowed=parse_xml(f.content);d["license"]=lic
            if paragraphs and allowed:
                d["status"]="licensed_fulltext";d["body"]=paragraphs
                d["selected_paragraph"]=evidence(paragraphs,topic)
                d["xml_url"]=link
            elif paragraphs:d["status"]="licence_not_confirmed"
            else:d["status"]="xml_without_body"
    if not d["selected_paragraph"]:d["selected_paragraph"]=d["abstract"]
    return d
def put(doc,n,item,src,subjects):
    doc.add_heading(str(n)+". "+item.get("title","Untitled"),level=2)
    doc.add_paragraph("Authors: "+str(item.get("authors","")))
    doc.add_paragraph("Journal: "+str(item.get("journal",""))+" ("+str(item.get("year",""))+")")
    doc.add_paragraph("PMID: "+item["pmid"]+" | PMCID: "+str(item.get("pmcid",""))+
          " | DOI: "+str(item.get("doi","")))
    doc.add_paragraph("PubMed: https://pubmed.ncbi.nlm.nih.gov/"+item["pmid"]+
          "/ | Sources: "+src+" | Topics: "+subjects)
    doc.add_paragraph("Full-text status: "+item["status"]+
          " | OA licence: "+str(item.get("license") or "unavailable"))
    if item.get("status")=="licensed_fulltext":
        doc.add_heading("VERBATIM RELEVANT PARAGRAPH FROM FULL TEXT",level=3)
        doc.add_paragraph(item.get("selected_paragraph") or "No relevant paragraph found.")
        doc.add_heading("FULL MAIN BODY TEXT (JATS XML; figures and references excluded)",level=3)
        for kind,line in item["body"]:
            if kind=="heading":doc.add_heading(line,level=3)
            else:doc.add_paragraph(line)
    else:
        doc.add_heading("ABSTRACT ONLY (full text unavailable / reuse not verified)",level=3)
        doc.add_paragraph(item.get("abstract") or "No abstract available")
def checkpoint(doc,rows):
    temp=DEST/"checkpoint_tmp.docx";doc.save(temp);os.replace(temp,RESULT)
    with open(REPORT,"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["PMID","status","PMCID","DOI","OA","body_paragraphs","licence"])
        for x in rows:w.writerow([x["pmid"],x["status"],x.get("pmcid",""),x.get("doi",""),
                                    x.get("isOpenAccess",""),len(x.get("body",[])),x.get("license","")])
def main():
    entries=csv_from_github("articles_for_github.csv")
    favorites=csv_from_github("selected_100_for_github.csv")
    assert len(entries)==679 and len(favorites)==100,"Manifest count mismatch"
    allids=OrderedDict()
    for r in entries:
        pmid=r.get("PMID","").strip()
        if not pmid.isdigit():continue
        x=allids.setdefault(pmid,{"files":set(),"topics":set()})
        x["files"].add(r.get("group",""))
    for r in favorites:
        pmid=r["PMID"].strip();sec=r.get("section","")
        if pmid in allids and sec.isdigit():allids[pmid]["topics"].add(int(sec))
    print("Input rows:",len(entries)," unique PMIDs:",len(allids)," top100:",len(favorites))
    doc=Document();doc.styles["Normal"].font.name="Calibri"
    doc.styles["Normal"].font.size=Pt(9)
    doc.add_heading("Nutritional Factors and the Gut–Brain Axis",0)
    doc.add_paragraph("Research corpus. Copyright respected: full main-body text is reproduced only from Europe PMC Open Access JATS XML where a compatible Creative Commons licence was identified. Other records contain only available abstracts.")
    logs=[]
    for n,(pmid,tag) in enumerate(allids.items(),1):
        file=CACHE/(pmid+".json")
        topic=min(tag["topics"]) if tag["topics"] else 0
        if file.exists():
            try:x=json.loads(file.read_text(encoding="utf-8"))
            except Exception:x=fetch(pmid,topic)
            if x.get("status") in ("metadata_unavailable","oa_fulltext_xml_not_available","xml_without_body"):
                x=fetch(pmid,topic)
                file.write_text(json.dumps(x,ensure_ascii=False),encoding="utf-8")
        else:
            x=fetch(pmid,topic)
            file.write_text(json.dumps(x,ensure_ascii=False),encoding="utf-8")
        tags="; ".join(TOPICS[k-1] for k in sorted(tag["topics"])) or "General bibliography"
        put(doc,n,x,", ".join(sorted(tag["files"])),tags);logs.append(x)
        print(f"[{n}/{len(allids)}] PMID {pmid}: {x['status']}",flush=True)
        if n%25==0:checkpoint(doc,logs);print("Checkpoint saved")
    checkpoint(doc,logs)
    outzip=DEST/"Nutrition_GutBrain_Results.zip"
    with zipfile.ZipFile(outzip,"w",zipfile.ZIP_DEFLATED) as z:
        z.write(RESULT,arcname=RESULT.name);z.write(REPORT,arcname=REPORT.name)
    print("DONE",RESULT,"statuses:",dict(Counter(x["status"] for x in logs)))
    try:
        from google.colab import files
        files.download(str(outzip))
    except ImportError:pass
if __name__=="__main__":main()
