#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONSM: live PubMed/PMC/Europe PMC/OpenAlex full-text-or-abstract collector.
Input  : ONSM_716_Records_244_Unique.html (716 occurrences / 244 unique PMIDs)
Output : ONSM_244_FullText_or_Abstract.docx + HTML/CSV/JSON audit and ZIP.
Only legitimately public sources are fetched. No paywalls or logins are bypassed.
"""
import argparse
import csv
import html
import io
import json
import os
import re
import threading
import time
import zipfile
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Inches, Pt
from lxml import etree

INPUT_NAME = "ONSM_716_Records_244_Unique.html"
WORD_NAME = "ONSM_244_FullText_or_Abstract.docx"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
OPENALEX = "https://api.openalex.org/works/"
WORK = Path("ONSM_244_Extraction_Work")
CACHE = WORK / "cache"
SOURCES = WORK / "raw_fulltexts"
STATE = threading.local()
HEADERS = {"User-Agent": "ONSM-PubMed-literature-study/1.0 (academic research)",
           "Accept": "application/json, application/xml, application/pdf, text/html, */*"}
MAX_RESPONSE_BYTES = 45 * 1024 * 1024  # Bound accidental huge downloads for Colab stability.

def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def sess():
    if not hasattr(STATE, "session"):
        s = requests.Session()
        s.headers.update(HEADERS)
        STATE.session = s
    return STATE.session

def request(url, params=None, max_bytes=MAX_RESPONSE_BYTES):
    """Return (payload, content_type, final_url, error). Retries server rate limits."""
    last = ""
    for attempt in range(4):
        try:
            with sess().get(url, params=params, timeout=(12, 48), stream=True,
                            allow_redirects=True) as res:
                if res.status_code == 404:
                    return None, "", str(res.url), "HTTP 404"
                if res.status_code in (429, 500, 502, 503, 504):
                    last = "HTTP "+str(res.status_code)
                    wait = res.headers.get("Retry-After","")
                    delay = max(2**attempt + 1, int(wait) if wait.isdigit() else 0)
                    time.sleep(min(delay, 35))
                    continue
                res.raise_for_status()
                data = bytearray()
                for chunk in res.iter_content(65536):
                    data.extend(chunk)
                    if len(data)>max_bytes:
                        raise ValueError("Remote file unexpectedly large; skipping to protect Colab")
                return bytes(data), res.headers.get("Content-Type",""), str(res.url), ""
        except (requests.RequestException, ValueError) as exc:
            last = type(exc).__name__ + ": " + str(exc)[:200]
            time.sleep(min(2**attempt+1, 14))
    return None,"",url,last or "Failed request"

def as_json(url, params=None):
    raw,ctype,final,error = request(url,params,max_bytes=5000000)
    if error: return {},error
    try: return json.loads(raw), ""
    except (ValueError,TypeError) as exc: return {},f"Bad JSON: {exc}"

def load_list(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    m = re.search(r'<script(?=[^>]*\bid=["\x27]onsm-data["\x27])[^>]*>(.*?)</script\s*>',raw,re.I|re.S)
    if not m: raise ValueError("Input HTML has no <script id='onsm-data'> embedded dataset.")
    data = json.loads(m.group(1))
    occurrences=data.get("records",[])
    if len(occurrences)!=716:
        raise ValueError(f"Expected 716 source occurrences, got {len(occurrences)}")
    records=OrderedDict()
    for item in occurrences:
        pmid=str(item.get("pmid","")).strip()
        if not pmid.isdigit(): raise ValueError("Bad PMID in HTML: "+repr(pmid))
        if pmid not in records:
            records[pmid]={
              "pmid":pmid, "title":item.get("title") or "",
              "authors":item.get("authors") or [], "doi":item.get("doi") or "",
              "abstract":item.get("abstract") or "", "pubdate":item.get("pubdate") or "",
              "year":item.get("year") or "", "types":item.get("types") or [],
              "categories":[], "file_names":[], "source_rows":[] }
        value=records[pmid]
        for key,val in (("categories",item.get("category")),("file_names",item.get("source_file"))):
            if val and val not in value[key]:value[key].append(val)
        value["source_rows"].append(item.get("row_index"))
        if len(item.get("abstract") or "")>len(value["abstract"]):
            value["abstract"]=item["abstract"]
    if len(records)!=244:
        raise ValueError(f"Expected 244 unique PMID, found {len(records)}")
    return list(records.values()), occurrences

def strip_markup(text):
    if not text: return ""
    # Europe PMC abstractText can contain XML/HTML markup; preserve content not markup.
    return BeautifulSoup(str(text),"html.parser").get_text(" ",strip=True)

def epmc_core(pmid):
    obj,error=as_json(EPMC+"/search",{
        "query":f"EXT_ID:{pmid} AND SRC:MED", "format":"json", 
        "resultType":"core","pageSize":1
    })
    if error:return {},error
    results=obj.get("resultList",{}).get("result",[])
    return (results[0] if results else {}),""

def openalex_work(doi):
    if not doi:return {},"No DOI for OpenAlex lookup"
    # OpenAlex endpoint accepts DOI URLs as work identifiers.
    work_url=OPENALEX+quote("https://doi.org/"+doi, safe=":/")
    params={}
    key=os.getenv("OPENALEX_API_KEY","").strip()
    if key:params["api_key"]=key
    data,error=as_json(work_url,params)
    if error:return {},error
    return data,""

def localname(el):
    if el is None:return ""
    return etree.QName(el).localname

def inline(el):
    text="".join(el.itertext())
    return re.sub(r"\s+"," ",html.unescape(text)).strip()

def parse_jats(raw):
    parser=etree.XMLParser(resolve_entities=False,load_dtd=False,no_network=True,
                           huge_tree=False,recover=False)
    root=etree.fromstring(raw,parser=parser)
    if localname(root)!="article":
        matches=root.xpath('.//*[local-name()="article"]')
        if not matches:raise ValueError("The XML has no <article> element")
        root=matches[0]
    body=root.xpath('./*[local-name()="body"]')
    if not body:raise ValueError("The XML has no full-text <body>")
    output=[]
    graphics=[]
    def add(kind,text):
        if isinstance(text,str) and text.strip():
            output.append({"kind":kind,"text":text})
    def traverse(node):
        tag=localname(node)
        if tag=="p":
            add("p",inline(node))
            for g in node.xpath('.//*[local-name()="inline-graphic"]'):
                graphics.extend(v for k,v in g.attrib.items() if "href" in k)
            return
        if tag in ("title","subtitle","label"):
            add("h" if tag!="label" else "p", inline(node))
            return
        if tag in ("disp-formula","inline-formula"):
            add("p",inline(node))
            return
        if tag=="fig":
            for child in node:
                t=localname(child)
                if t=="label":add("h",inline(child))
                elif t=="caption":
                    for c in child:add("h" if localname(c)=="title" else "p",inline(c))
            graphics.extend(v for g in node.xpath('.//*[local-name()="graphic"]')
                            for k,v in g.attrib.items() if "href" in k)
            return
        if tag in ("table-wrap","table"):
            if tag=="table-wrap":
                for ch in node:
                    if localname(ch) in ("caption","label"):
                        add("p",inline(ch))
                for table in node.xpath('.//*[local-name()="table"]'):
                    traverse(table)
                for foot in node.xpath('./*[local-name()="table-wrap-foot"]'):
                    add("p",inline(foot))
                return
            lines=[]
            for tr in node.xpath('.//*[local-name()="tr"]'):
                row=[inline(c) for c in tr if localname(c) in ("th","td")]
                if row: lines.append(row)
            if lines:output.append({"kind":"table","rows":lines})
            return
        if tag in ("ref","mixed-citation","element-citation"):
            add("p",inline(node))
            return
        for child in node:
            traverse(child)
    # Only full article body and back matter: no abstract substitution.
    traverse(body[0])
    back=root.xpath('./*[local-name()="back"]')
    for b in back:
        add("h","Back matter and references")
        traverse(b)
    wordcount=sum(len(b.get("text","")) for b in output)
    wordcount+=sum(len(c) for b in output if b["kind"]=="table" for r in b["rows"] for c in r)
    if wordcount<280:raise ValueError("JATS body unexpectedly short; not marked as full text")
    license_nodes=root.xpath('.//*[local-name()="license"]')
    license_text=" | ".join(inline(l) for l in license_nodes)[:1100]
    return output,license_text,graphics

def parse_bioc(raw):
    payload=json.loads(raw)
    documents=(payload.get("documents") or []) if isinstance(payload,dict) else []
    if not documents and isinstance(payload,list):
        documents=[item for col in payload if isinstance(col,dict)
                   for item in (col.get("documents") or [])]
    if not documents:raise ValueError("PMC BioC returned no article documents")
    allblocks=[];nonabstract=[]
    for passage in documents[0].get("passages",[]):
        text=str(passage.get("text") or "")
        if not text.strip():continue
        infons=passage.get("infons") or {}
        typ=str(infons.get("type") or infons.get("section_type") or "").lower()
        section=str(infons.get("section") or "").lower()
        if "abstract" not in typ+" "+section and "title" not in typ:
            nonabstract.append(text)
        allblocks.append({"kind":"h" if "title" in typ else "p","text":text})
    if len("".join(nonabstract))<400:
        raise ValueError("BioC result lacks sufficient non-abstract article content")
    return allblocks,"",[]

def parse_pdf(raw):
    import fitz
    blocks=[]
    with fitz.open(stream=raw,filetype="pdf") as doc:
        for page_no,page in enumerate(doc,1):
            t=page.get_text("text",sort=True)
            if t.strip():blocks.append({"kind":"p","text":t})
    if sum(len(b["text"]) for b in blocks)<800:
        raise ValueError("The public PDF has no readable full text (may be scanned)")
    return blocks,"",[]

def parse_docx(raw):
    doc=Document(io.BytesIO(raw))
    blocks=[]
    for item in doc.element.body.iterchildren():
        if item.tag.endswith("}p"):
            from docx.text.paragraph import Paragraph
            obj=Paragraph(item,doc)
            if obj.text:
                blocks.append({"kind":"h" if obj.style.name.startswith("Heading") else "p",
                               "text":obj.text})
        elif item.tag.endswith("}tbl"):
            from docx.table import Table
            t=Table(item,doc)
            matrix=[[cell.text for cell in line.cells] for line in t.rows]
            if matrix:blocks.append({"kind":"table","rows":matrix})
    if sum(len(b.get("text","")) for b in blocks)<500:raise ValueError("Public DOCX has too little full text")
    return blocks,"",[]

def parse_public_html(raw):
    soup=BeautifulSoup(raw,"html.parser")
    for item in soup.select("script,style,nav,header,footer,aside,form,.cookie-banner,.related-articles"):
        item.decompose()
    container=None
    for selector in ("article .article-body","article .full-text","#article-body",
                     "#fullText","main article","article","main"):
        candidate=soup.select_one(selector)
        if candidate and len(candidate.get_text(" ",strip=True))>1300:
            container=candidate
            break
    if container is None:raise ValueError("Full article body not found in public HTML")
    content=container.get_text(" ",strip=True).lower()
    if any(t in content[:1200] for t in ["purchase access to this article",
          "subscribe to read","log in to access the full text"]):
        raise ValueError("Publisher HTML appears to require subscription")
    blocks=[]
    for el in container.find_all(["h1","h2","h3","h4","p","blockquote","li","table"]):
        if el.find_parent(["p","li","blockquote","table"]) is not None:continue
        if el.name=="table":
            table=[[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"])]
                   for tr in el.find_all("tr")]
            table=[r for r in table if r]
            if table:blocks.append({"kind":"table","rows":table})
        else:
            value=el.get_text(" ",strip=True)
            if value:blocks.append({"kind":"h" if el.name.startswith("h") else "p","text":value})
    if sum(len(b.get("text","")) for b in blocks)<1100:
        raise ValueError("Public webpage does not contain a verifiable complete article")
    return blocks,"",[]

def extract_public_link(url):
    if not url or not url.startswith("https://"):
        raise ValueError("No HTTPS public full-text URL supplied")
    host=urlparse(url).hostname or ""
    if host.endswith("pmc.ncbi.nlm.nih.gov"):
        raise ValueError("PMC article pages are not scraped; dedicated APIs are used")
    raw,ctype,final,error=request(url)
    if error:raise ValueError(error)
    # reject a login/verification page rather than claiming it is full text
    if raw[:4]==b"%PDF":
        blocks,license_note,graphics=parse_pdf(raw);suffix=".pdf"
    elif raw[:2]==b"PK" and (final.lower().split("?")[0].endswith(".docx")
                             or "wordprocessingml" in ctype.lower()):
        blocks,license_note,graphics=parse_docx(raw);suffix=".docx"
    elif "html" in ctype.lower() or b"<html" in raw[:1000].lower():
        blocks,license_note,graphics=parse_public_html(raw);suffix=".html"
    else:raise ValueError("The public link did not provide readable full-text PDF/HTML/DOCX")
    return blocks,license_note,graphics,raw,suffix,final

def lookup_free_links(core,openalex):
    options=[]
    for it in (core.get("fullTextUrlList") or {}).get("fullTextUrl",[]) or []:
        u=it.get("url") or ""
        availability=str(it.get("availability") or "").lower()
        if u.startswith("https://") and ("free" in availability or "open" in availability):
            options.append(("Europe PMC public copy",u))
    if openalex.get("open_access",{}).get("is_oa"):
        locs=[openalex.get("best_oa_location") or {}]
        locs.extend(openalex.get("locations") or [])
        for loc in locs:
            if not loc.get("is_oa"):continue
            for field in ("pdf_url","landing_page_url"):
                url=loc.get(field) or ""
                if url.startswith("https://"):options.append(("OpenAlex OA location",url))
        url=(openalex.get("open_access") or {}).get("oa_url") or ""
        if url.startswith("https://"):options.append(("OpenAlex OA URL",url))
    output=[];seen=set()
    for label,url in options:
        if url not in seen:seen.add(url);output.append((label,url))
    return output[:8]  # Avoid repetitive requests to the same article hosts.

def retrieve(row):
    pmid=row["pmid"]
    result={"pmid":pmid,"title":row["title"],"doi":row["doi"],
            "checked_at":utcnow(),"status":"ABSTRACT_ONLY",
            "access":"No publicly retrievable full text was confirmed",
            "method":"","full_text_url":"","source_file":"",
            "full_text_blocks":[],"abstract":row.get("abstract") or "",
            "license":"","unembedded_graphics":[],"errors":[],"openalex_oa":None,
            "pmcid":"","epmc_available":False}
    core,eerr=epmc_core(pmid)
    if eerr:result["errors"].append("Europe PMC metadata: "+eerr)
    else:
        result["epmc_available"]=bool(core)
        if not result["abstract"] and core.get("abstractText"):
            result["abstract"]=strip_markup(core["abstractText"])
    pmcid=str(core.get("pmcid") or "")
    result["pmcid"]=pmcid
    def success(method,source,blocks,lic,graphics,raw,suffix):
        name=SOURCES/(pmid+suffix)
        name.write_bytes(raw)
        result.update(status="FULL_TEXT",access="Publicly accessible full text retrieved",
                      method=method,full_text_url=source,
                      source_file=str(name),full_text_blocks=blocks,
                      license=lic,unembedded_graphics=graphics)
        return result
    if re.fullmatch(r"PMC\d+",pmcid):
        url=f"{EPMC}/{pmcid}/fullTextXML"
        raw,ct,final,error=request(url)
        if raw:
            try:
                blocks,lic,graphics=parse_jats(raw)
                return success("Europe PMC JATS XML",final,blocks,lic,graphics,raw,".xml")
            except Exception as exc:result["errors"].append("JATS parser: "+str(exc)[:180])
        elif error:result["errors"].append("JATS: "+error)
    # NCBI official PMC open-access full text BioC API accepts either PMID or PMCID
    identifier=pmcid if re.fullmatch(r"PMC\d+",pmcid) else pmid
    bioc_url=f"{BIOC}/{identifier}/unicode"
    raw,ct,final,error=request(bioc_url,max_bytes=16000000)
    if raw:
        try:
            blocks,lic,graphics=parse_bioc(raw)
            return success("NCBI PMC Open Access BioC",final,blocks,lic,graphics,raw,"_bioc.json")
        except Exception as exc:result["errors"].append("BioC: "+str(exc)[:180])
    elif error:result["errors"].append("BioC: "+error)
    oa,oa_error=openalex_work(row.get("doi",""))
    if oa_error:result["errors"].append("OpenAlex: "+oa_error)
    result["openalex_oa"]=bool((oa.get("open_access") or {}).get("is_oa")) if oa else None
    if core.get("isOpenAccess")=="Y" or result["openalex_oa"] is True:
        result["access"]="OA metadata found, but complete text could not be extracted"
    for label,source in lookup_free_links(core,oa):
        try:
            blocks,lic,graphics,blob,suffix,final=extract_public_link(source)
            return success(label,final,blocks,lic,graphics,blob,suffix)
        except Exception as exc:
            result["errors"].append(label+": "+str(exc)[:180])
    if not result["abstract"]:
        result["access"]+="; abstract also absent"
    if not core and oa_error and eerr:
        result["access"]="External verification services failed; status uncertain"
    return result

def add_field(doc,label,value):
    if value is None or value=="":return
    p=doc.add_paragraph(style="Normal")
    p.add_run(label+": ").bold=True
    if isinstance(value,list):value="; ".join(map(str,value))
    p.add_run(str(value))

def add_blocks(doc,blocks):
    for b in blocks:
        kind=b.get("kind")
        if kind=="table":
            items=b.get("rows") or []
            if not items:continue
            width=max(len(r) for r in items)
            if width>12:
                for r in items:doc.add_paragraph(" | ".join(r))
                continue
            table=doc.add_table(rows=0,cols=width)
            table.style="Table Grid"
            for r in items:
                cells=table.add_row().cells
                for j,text in enumerate(r):
                    cells[j].text=text
            doc.add_paragraph()
        elif kind=="h":
            doc.add_heading(b.get("text") or "",level=2)
        elif kind=="p":
            doc.add_paragraph(b.get("text") or "")

def build_word(rows,results,filename):
    doc=Document()
    section=doc.sections[0]
    section.top_margin=section.bottom_margin=Inches(.7)
    section.left_margin=section.right_margin=Inches(.72)
    normal=doc.styles["Normal"]
    normal.font.name="Arial"
    normal.font.size=Pt(9)
    normal.paragraph_format.space_after=Pt(5)
    nfull=sum(results[r["pmid"]]["status"]=="FULL_TEXT" for r in rows)
    doc.add_heading("ONSM — Full Text When Available, Original Abstract Otherwise",0)
    doc.add_paragraph(f"Unique papers: {len(rows)} | Full texts obtained: {nfull} | Abstract-only: {len(rows)-nfull}")
    doc.add_paragraph("The paper's source prose is not translated or rewritten. XML/HTML/PDF-to-Word "
                      "conversion can change layout and paragraph whitespace, formulas, figures and tables; "
                      "original fetched sources are preserved in a separate ZIP.")
    doc.add_paragraph("Classification: ABSTRACT_ONLY means no complete public copy could be extracted during "
                      "this run; it does not prove that university subscription is required.")
    for ix,row in enumerate(rows,1):
        status=results[row["pmid"]]
        doc.add_page_break()
        doc.add_heading(f"{ix}. {row['title']}",level=1)
        add_field(doc,"Authors",row.get("authors"))
        add_field(doc,"Publication date",row.get("pubdate") or row.get("year"))
        add_field(doc,"Publication type",row.get("types"))
        add_field(doc,"DOI",row.get("doi"))
        add_field(doc,"PMID",row["pmid"])
        add_field(doc,"PMCID",status.get("pmcid"))
        add_field(doc,"PubMed URL","https://pubmed.ncbi.nlm.nih.gov/"+row["pmid"]+"/")
        add_field(doc,"Source HTML files",row.get("file_names"))
        add_field(doc,"Original occurrences",row.get("source_rows"))
        add_field(doc,"Access assessment",status["access"])
        add_field(doc,"Live check",status["checked_at"])
        if status["status"]=="FULL_TEXT":
            add_field(doc,"Full-text extraction source",status["full_text_url"])
            add_field(doc,"Extraction method",status["method"])
            add_field(doc,"License/terms if available",status.get("license"))
            doc.add_heading("FULL TEXT — original wording",level=2)
            add_blocks(doc,status.get("full_text_blocks") or [])
        else:
            doc.add_heading("ABSTRACT ONLY — full text was not retrieved",level=2)
            doc.add_paragraph(status.get("abstract") or row.get("abstract") or
                              "[No source abstract available]")
            add_field(doc,"Reason/evidence",status.get("errors",[]))
        if ix%10==0:print(f"Word assembled: {ix}/{len(rows)}",flush=True)
    doc.save(filename)

def create_status_html(rows,results,filename):
    def e(s):return html.escape(str(s or ""),quote=True)
    full=sum(results[r["pmid"]]["status"]=="FULL_TEXT" for r in rows)
    items=[]
    for row in rows:
        r=results[row["pmid"]]
        ok=r["status"]=="FULL_TEXT"
        extra=e(" | ".join(r.get("errors") or []))
        link=e(r.get("full_text_url") or "https://pubmed.ncbi.nlm.nih.gov/"+row["pmid"]+"/")
        items.append(
          f'<article class="{"ok" if ok else "fail"}"><h3>{e(row["title"])}</h3>'
          f'<div><b>PMID:</b> {e(row["pmid"])} | <b>DOI:</b> {e(row.get("doi"))}</div>'
          f'<div><b>Result:</b> {e("Full text obtained" if ok else "Abstract only")}</div>'
          f'<div><b>Access:</b> {e(r["access"])}</div>'
          f'<div><b>Extracted by:</b> {e(r.get("method"))}</div>'
          f'<div><a href="{link}" rel="noopener" target="_blank">Article / public source</a></div>'
          f'<details><summary>Abstract & verification notes</summary><pre>{e(r.get("abstract"))}</pre>'
          f'<p>{extra}</p></details></article>')
    content='''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ONSM 244: Live access results</title><style>
body{margin:0;background:#f6f8fc;color:#243851;font:14px/1.8 Tahoma,Arial,sans-serif}
header{background:#153c66;color:white;padding:25px}main{max-width:1000px;margin:auto;padding:16px}
input{width:100%;padding:12px;border:1px solid #bfd0e2;border-radius:9px;box-sizing:border-box}
article{border:1px solid #dbe5ee;background:#fff;margin:12px 0;padding:15px;border-radius:12px}
article.ok{border-right:5px solid #2d8860}article.fail{border-right:5px solid #ad7331}
h3{text-align:left;direction:ltr}a{color:#17629b;overflow-wrap:anywhere}
pre{white-space:pre-wrap;direction:ltr;text-align:left;font:12px/1.5 Arial,sans-serif}
summary{cursor:pointer}</style></head><body>'''
    content+=f'<header><h1>ONSM Live Full Text or Abstract — 244 articles</h1><p>Full text: {full} | Abstract only: {len(rows)-full}. Status is based on this Colab run, not a guaranteed paywall classification.</p></header><main><input id="q" type="search" placeholder="Search..." oninput="filterCards()"><div id="articles">'
    content+="\n".join(items)
    content+='''</div></main><script>function filterCards(){let q=document.getElementById('q').value.toLowerCase();
for(const a of document.querySelectorAll('#articles article'))
a.hidden=!a.textContent.toLowerCase().includes(q);}</script></body></html>'''
    Path(filename).write_text(content,encoding="utf-8")

def reports(rows,results):
    with open("ONSM_244_Access_Report.csv","w",newline="",encoding="utf-8-sig") as f:
        writer=csv.writer(f)
        writer.writerow(["pmid","title","doi","status","access_assessment","source_url",
                         "method","original_occurrences","checked_at","errors"])
        for row in rows:
            r=results[row["pmid"]]
            writer.writerow([row["pmid"],row["title"],row.get("doi",""),r["status"],
                            r["access"],r["full_text_url"],r["method"],
                            len(row["source_rows"]),r["checked_at"],
                            " | ".join(r.get("errors") or [])])
    with open("ONSM_244_Access_Report.json","w",encoding="utf8") as f:
        json.dump({"created":utcnow(),"results":[
            {k:v for k,v in results[r["pmid"]].items() if k!="full_text_blocks"}
            for r in rows]},f,ensure_ascii=False,indent=2)

def self_test(path):
    rows,raw=load_list(path)
    assert len(rows)==244 and len(raw)==716
    assert all(r["abstract"] and r["doi"] for r in rows)
    fixture=b'<article><body><sec><title>Methods</title><p>'+(b'Text with no paraphrasing. '*26)+b'</p></sec><table-wrap><caption><title>Table 1</title></caption><table><tr><th>A</th><td>5</td></tr></table></table-wrap></body><back><ref-list><ref><mixed-citation>Reference 2026.</mixed-citation></ref></ref-list></back></article>'
    parsed,_,_=parse_jats(fixture)
    assert any(b["kind"]=="table" for b in parsed)
    assert any("Reference 2026." in b.get("text","") for b in parsed)
    assert any("Text with no paraphrasing." in b.get("text","") for b in parsed)
    print("SELF TEST PASSED: 716 original occurrences, 244 unique papers; JATS test passed.",flush=True)

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input",default=INPUT_NAME)
    cli.add_argument("--output",default=WORD_NAME)
    cli.add_argument("--workers",type=int,default=3)
    cli.add_argument("--retry-abstracts",action="store_true",
                     help="Repeat failed/incomplete cached retrievals.")
    cli.add_argument("--auto-download",action="store_true")
    cli.add_argument("--self-test",action="store_true")
    args=cli.parse_args()
    if args.self_test:
        self_test(args.input)
        return
    rows,source=load_list(args.input)
    CACHE.mkdir(parents=True,exist_ok=True)
    SOURCES.mkdir(parents=True,exist_ok=True)
    result={}
    to_check=[]
    for row in rows:
        file=CACHE/(row["pmid"]+".json")
        try:
            saved=json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
        except (ValueError,OSError):
            saved={}
        if saved.get("status")=="FULL_TEXT" or (saved.get("status")=="ABSTRACT_ONLY" and not args.retry_abstracts):
            result[row["pmid"]]=saved
        else:
            to_check.append(row)
    print(f"Total: {len(source)} records, {len(rows)} unique; live checks: {len(to_check)}",flush=True)
    with ThreadPoolExecutor(max_workers=max(1,min(4,args.workers))) as pool:
        futures={pool.submit(retrieve,row):row for row in to_check}
        for ix,fut in enumerate(as_completed(futures),1):
            row=futures[fut];pmid=row["pmid"]
            try:
                outcome=fut.result()
            except Exception as ex:
                outcome={"pmid":pmid,"title":row["title"],"doi":row.get("doi",""),
                         "status":"ABSTRACT_ONLY","checked_at":utcnow(),
                         "access":"Technical failure during online check; access uncertain",
                         "method":"","full_text_url":"","source_file":"",
                         "full_text_blocks":[],"abstract":row["abstract"],
                         "license":"","errors":[str(ex)[:280]]}
            result[pmid]=outcome
            (CACHE/(pmid+".json")).write_text(
                json.dumps(outcome,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"[{ix}/{len(to_check)}] PMID {pmid}: {outcome['status']}",flush=True)
    build_word(rows,result,args.output)
    create_status_html(rows,result,"ONSM_244_Live_Status.html")
    reports(rows,result)
    originals="ONSM_244_Raw_FullText_Sources.zip"
    with zipfile.ZipFile(originals,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(SOURCES.glob("*")):
            if file.is_file():z.write(file,"original_sources/"+file.name)
    bundle="ONSM_244_Colab_Results.zip"
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for path in [args.output,"ONSM_244_Live_Status.html",
                     "ONSM_244_Access_Report.csv","ONSM_244_Access_Report.json"]:
            z.write(path,arcname=Path(path).name)
    nfull=sum(result[x["pmid"]]["status"]=="FULL_TEXT" for x in rows)
    print(f"Finished: {nfull} full text; {len(rows)-nfull} original abstract only.",flush=True)
    print(f"Files created: {args.output}, {bundle}, {originals}",flush=True)
    if args.auto_download:
        try:
            from google.colab import files
            files.download(bundle)
        except ImportError:
            print("Colab downloads unavailable; files are saved in current directory.",flush=True)

if __name__=="__main__":
    main()
