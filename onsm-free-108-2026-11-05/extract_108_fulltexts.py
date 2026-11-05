#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONSM 108 free-full-text research collection.
Input: ONSM_Free_108_Articles.html (embedded JSON, exactly 108 unique PMIDs).
LIVE retrieval: Europe PMC JATS XML -> NCBI PMC BioC OA API ->
originally verified, publicly accessible publisher PDF/DOCX/HTML link.
Output: ONSM_108_Full_Texts.docx, status HTML, audit CSV/JSON,
and raw source copies (for checking the original wording).
No abstracts are substituted for missing full text.
"""
from __future__ import annotations
import argparse
import csv
import html
import io
import json
import re
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.enum.text import WD_BREAK
from docx.shared import Inches, Pt
from lxml import etree

EUROPE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
USER_AGENT = "ONSM-personal-academic-research/1.0 (contact: researcher)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, application/pdf, text/html, */*"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
MAX_BYTES = 50 * 1024 * 1024
STATE = Path("ONSM_108_Work")
FILES = STATE / "original_sources"
RECORDS = STATE / "records"
WARNINGS = []

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg):
    print(msg, flush=True)

def xml_name(el):
    try:
        return etree.QName(el).localname
    except Exception:
        return ""

def inline_text(el):
    # No translation, rewriting, summarizing, or spelling correction.
    # Normalize XML layout whitespace only, to make text usable in Word.
    value = "".join(el.itertext())
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def get(url, params=None, max_bytes=MAX_BYTES, accepts_404=False):
    """Back off on rate limits, bound bytes, reject inaccessible/login responses."""
    last = None
    for attempt in range(4):
        try:
            with SESSION.get(url, params=params, timeout=(15, 60), stream=True,
                             allow_redirects=True) as response:
                code = response.status_code
                if code == 404 and accepts_404:
                    return None, None, str(response.url), "HTTP 404"
                if code in (429, 500, 502, 503, 504):
                    retry_after = response.headers.get("Retry-After", "")
                    delay = max(2 ** attempt + 1, int(retry_after) if retry_after.isdigit() else 0)
                    last = f"HTTP {code}"
                    time.sleep(min(delay, 35))
                    continue
                response.raise_for_status()
                result = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    result.extend(chunk)
                    if len(result) > max_bytes:
                        raise ValueError("Source exceeded configured safety size limit")
                return bytes(result), response.headers.get("Content-Type",""), str(response.url), None
        except (requests.RequestException, ValueError) as exc:
            last = f"{type(exc).__name__}: {str(exc)[:220]}"
            time.sleep(min(2 ** attempt + 1, 12))
    return None, None, url, last or "Unknown download error"

def load_input(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    match = re.search(
        r'<script(?=[^>]*\bid=["\x27]onsm-free-records["\x27])[^>]*>(.*?)</script\s*>',
        text, re.I | re.S
    )
    if not match:
        raise ValueError("The input HTML does not contain onsm-free-records JSON.")
    rows = json.loads(match.group(1)).get("papers", [])
    ids = [str(x.get("pmid","")) for x in rows]
    if len(rows) != 108 or len(set(ids)) != 108 or any(not i.isdigit() for i in ids):
        raise ValueError(f"Expected exactly 108 unique numeric PMIDs; got {len(rows)}/{len(set(ids))}.")
    return rows

def epmc_core(pmid):
    raw, ctype, final, error = get(EUROPE + "/search", {
        "query": f"EXT_ID:{pmid} AND SRC:MED",
        "format": "json", "resultType": "core", "pageSize": 1
    }, max_bytes=4000000)
    if not raw:
        return {}, error or "Europe PMC did not respond"
    try:
        data = json.loads(raw)
        arr = data.get("resultList", {}).get("result", [])
        return (arr[0] if arr else {}), None
    except (ValueError, TypeError, KeyError) as ex:
        return {}, f"Invalid Europe PMC JSON: {ex}"

def extract_license(root):
    texts = [inline_text(x) for x in root.xpath('.//*[local-name()="license-p"]')]
    links = [v for el in root.xpath('.//*[local-name()="license"]') for k,v in el.attrib.items()
             if "href" in k and v]
    return (" / ".join(texts[:3] + links[:3]))[:1600]

def parse_jats(raw):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, recover=False)
    root = etree.fromstring(raw, parser=parser)
    if xml_name(root) != "article":
        found = root.xpath('.//*[local-name()="article"]')
        if not found:
            raise ValueError("JATS response does not contain an article")
        root = found[0]
    bodies = root.xpath('./*[local-name()="body"]')
    if not bodies:
        raise ValueError("JATS is missing the full article body")
    blocks = []
    embedded_graphics = []
    def add(kind, text):
        if isinstance(text, str) and text.strip():
            blocks.append({"kind": kind, "text": text})
    def crawl(node, depth=0):
        tag = xml_name(node)
        if tag in ("p","named-content","def"):
            # Avoid duplicates by consuming the entire paragraph once.
            if tag=="p" or (tag=="def" and not node.xpath('./*[local-name()="p"]')):
                add("p", inline_text(node))
                return
        if tag in ("title","label","subtitle") and xml_name(node.getparent()) not in ("table-wrap","fig"):
            add("h" if tag!="label" else "p",inline_text(node))
            return
        if tag in ("ref","mixed-citation","element-citation"):
            add("p", inline_text(node))
            return
        if tag=="fig":
            for child in node:
                if xml_name(child)=="label": add("h",inline_text(child))
                elif xml_name(child)=="caption":
                    for caption in child:
                        if xml_name(caption)=="title": add("h",inline_text(caption))
                        else: add("p",inline_text(caption))
            for g in node.xpath('.//*[local-name()="graphic" or local-name()="inline-graphic"]'):
                embedded_graphics.extend([v for k,v in g.attrib.items() if "href" in k])
            return
        if tag in ("table-wrap","table"):
            if tag=="table-wrap":
                for c in node:
                    if xml_name(c)=="label": add("h", inline_text(c))
                    elif xml_name(c)=="caption": add("p", inline_text(c))
                tables=node.xpath('.//*[local-name()="table"]')
                for t in tables: crawl(t,depth+1)
                for c in node:
                    if xml_name(c)=="table-wrap-foot": crawl(c,depth+1)
            else:
                rows=[]
                for tr in node.xpath('.//*[local-name()="tr"]'):
                    cells=[inline_text(cell) for cell in tr if xml_name(cell) in ("th","td")]
                    if cells:rows.append(cells)
                if rows:blocks.append({"kind":"table","rows":rows})
            return
        if tag in ("disp-formula","inline-formula"):
            val=inline_text(node)
            if val: add("p",val)
            return
        if tag in ("graphic","inline-graphic"):
            embedded_graphics.extend([v for k,v in node.attrib.items() if "href" in k])
            return
        for child in node:
            crawl(child, depth+1)
    for ar in root.xpath('./*[local-name()="front"]/*[local-name()="article-meta"]/*[local-name()="abstract"]'):
        add("h","ABSTRACT (source article)")
        crawl(ar)
    add("h","ARTICLE BODY")
    crawl(bodies[0])
    for node in root.xpath('./*[local-name()="back"]'):
        add("h","BACK MATTER / REFERENCES")
        crawl(node)
    raw_len=sum(len(x.get("text","")) for x in blocks if x["kind"]!="table")
    raw_len+=sum(len(v) for x in blocks if x["kind"]=="table" for row in x["rows"] for v in row)
    if raw_len < 500:
        raise ValueError(f"JATS returned only {raw_len} readable characters")
    return blocks, extract_license(root), embedded_graphics

def parse_bioc(raw):
    data = json.loads(raw)
    docs = data.get("documents", []) if isinstance(data, dict) else []
    if not docs:
        raise ValueError("PMC BioC API returned no documents")
    blocks=[]
    for passage in docs[0].get("passages", []):
        value=passage.get("text")
        if not value:
            continue
        kind=(passage.get("infons") or {}).get("type","").lower()
        blocks.append({"kind":"h" if kind in ("title","section_title","title_1") else "p",
                       "text":str(value)})
    if sum(len(x["text"]) for x in blocks)<500:
        raise ValueError("PMC BioC response did not contain a complete readable article")
    return blocks, (docs[0].get("infons") or {}).get("license",""), []

def source_pmid(row, core):
    pmcid=core.get("pmcid") or ""
    if not pmcid:
        m=re.search(r"(PMC\d+)",row.get("free_url",""),re.I)
        pmcid=m.group(1).upper() if m else ""
    return pmcid if re.fullmatch(r"PMC\d+",pmcid) else ""

def robots_allows(url):
    """Conservative public-HTML check. PDF/DOCX direct download is not site crawling."""
    u=urlparse(url)
    if u.scheme not in ("http","https"):
        return False
    robots=u.scheme+"://"+u.netloc+"/robots.txt"
    try:
        rp=RobotFileParser()
        content,ctype,final,error=get(robots,max_bytes=800000,accepts_404=True)
        if error and error!="HTTP 404":
            return False
        if error=="HTTP 404":
            return True
        rp.parse((content or b"").decode("utf-8",errors="replace").splitlines())
        return rp.can_fetch(USER_AGENT,url)
    except Exception:
        return False

def parse_pdf(raw):
    import fitz
    doc=fitz.open(stream=raw,filetype="pdf")
    blocks=[]
    for i,page in enumerate(doc):
        # Plain text is extracted without rewriting. PDF ordering depends on PDF internals.
        content=page.get_text("text",sort=True)
        if content.strip():
            blocks.append({"kind":"p","text":content})
    if sum(len(b["text"]) for b in blocks)<500:
        raise ValueError("PDF did not contain selectable full text (possibly image-only)")
    return blocks, "", []

def parse_docx(raw):
    doc=Document(io.BytesIO(raw))
    blocks=[]
    for item in doc.element.body.iterchildren():
        if item.tag.endswith("}p"):
            from docx.text.paragraph import Paragraph
            p=Paragraph(item,doc)
            if p.text:
                blocks.append({"kind":"h" if p.style and p.style.name.startswith("Heading") else "p","text":p.text})
        elif item.tag.endswith("}tbl"):
            from docx.table import Table
            table=Table(item,doc)
            rows=[[cell.text for cell in r.cells] for r in table.rows]
            if rows:blocks.append({"kind":"table","rows":rows})
    if sum(len(x.get("text","")) for x in blocks)<300:
        raise ValueError("Publisher DOCX did not contain a full readable document")
    return blocks, "", []

def parse_publisher_html(raw):
    soup=BeautifulSoup(raw,"html.parser")
    for bad in soup.select("script,style,nav,header,footer,aside,form,.cookie-banner,.references-widget"):
        bad.decompose()
    area=None
    for sel in ("article .article-body","article .full-text","div.article-body","div#article-body",
                "#fullText","article","main article"):
        area=soup.select_one(sel)
        if area and len(area.get_text(" ",strip=True))>650:
            break
        area=None
    if area is None:
        raise ValueError("Cannot locate a verified full-text article body; avoiding webpage boilerplate")
    clean=area.get_text(" ",strip=True).lower()
    if ("purchase access" in clean or "subscribe to access" in clean) and len(clean)<2500:
        raise ValueError("Webpage appears to require payment or login")
    blocks=[]
    for el in area.find_all(["h1","h2","h3","h4","p","li","blockquote","table"]):
        if el.find_parent(["p","li","blockquote","table"]) is not None and el.name!="table":
            continue
        if el.name=="table":
            rows=[[re.sub(r"\s+"," ",c.get_text(" ",strip=True)) for c in tr.find_all(["td","th"])]
                  for tr in el.find_all("tr")]
            rows=[r for r in rows if r]
            if rows:blocks.append({"kind":"table","rows":rows})
        else:
            val=el.get_text(" ",strip=True)
            if val:
                blocks.append({"kind":"h" if el.name.startswith("h") else "p","text":val})
    if sum(len(x.get("text","")) for x in blocks)<600:
        raise ValueError("Publisher page is not a complete extractable article")
    return blocks, "", []

def parse_public_link(row):
    url=row.get("free_url","").strip()
    if not url:
        raise ValueError("No verified free URL in input record")
    netloc=urlparse(url).netloc.lower()
    if "pmc.ncbi.nlm.nih.gov" in netloc:
        raise ValueError("PMC pages are not bulk-scraped; used approved APIs instead")
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS source links are fetched")
    # Respect robots directives for publisher sites before requesting their pages.
    if not robots_allows(url):
        raise ValueError("Publisher robots policy unavailable or does not permit automated retrieval")
    raw,ctype,final,error=get(url)
    if not raw:raise ValueError(f"Publisher source: {error or 'empty response'}")
    fmt=(ctype or "").lower()
    if raw[:4]==b"%PDF":return parse_pdf(raw)+(raw,".pdf",final,"publisher_pdf")
    if raw[:2]==b"PK" and ("wordprocessingml" in fmt or final.lower().split("?")[0].endswith(".docx")):
        return parse_docx(raw)+(raw,".docx",final,"publisher_docx")
    if b"<html" in raw[:1000].lower() or "html" in fmt:
        return parse_publisher_html(raw)+(raw,".html",final,"publisher_html")
    raise ValueError("Remote URL did not deliver a recognized full-text PDF, DOCX, or HTML article")

def run_one(row):
    pmid=str(row["pmid"])
    errors=[]
    out={"pmid":pmid,"title":row["title"],"doi":row.get("doi",""),
         "authors":row.get("authors",[]),"published":row.get("published",""),
         "free_url_previous":row.get("free_url",""),
         "original_verifier":row.get("verified_source",""),
         "checked_at":ts(),"status":"FAILED","errors":errors,
         "method":"","source_url":"","pmcid":"","license":"",
         "graphics_not_embedded":[],"blocks":[]}
    core,issue=epmc_core(pmid)
    if issue:errors.append("Europe PMC metadata: "+issue)
    pmcid=source_pmid(row,core)
    out["pmcid"]=pmcid
    if pmcid:
        url=f"{EUROPE}/{pmcid}/fullTextXML"
        raw,ctype,final,error=get(url,accepts_404=True)
        if raw:
            try:
                blocks,license_note,graphics=parse_jats(raw)
                filename=FILES/(pmid+".xml")
                filename.write_bytes(raw)
                out.update(status="EXTRACTED",method="europepmc_jats",
                           source_url=final,source_file=str(filename),
                           blocks=blocks,license=license_note,
                           graphics_not_embedded=graphics)
                return out
            except Exception as exc:
                errors.append("JATS parse: "+str(exc)[:220])
        elif error:errors.append("Europe PMC fullTextXML: "+error)
        # The NCBI BioC endpoint is documented for the PMC OA subset.
        api=f"{BIOC}/{pmcid}/unicode"
        raw,ctype,final,error=get(api,accepts_404=True)
        if raw:
            try:
                blocks,license_note,graphics=parse_bioc(raw)
                filename=FILES/(pmid+"_bioc.json")
                filename.write_bytes(raw)
                out.update(status="EXTRACTED",method="ncbi_bioc",
                           source_url=final,source_file=str(filename),
                           blocks=blocks,license=license_note,
                           graphics_not_embedded=graphics)
                return out
            except Exception as exc:
                errors.append("BioC parse: "+str(exc)[:220])
        elif error:errors.append("NCBI BioC full text: "+error)
    try:
        blocks,license_note,graphics,raw,suffix,url,method=parse_public_link(row)
        filename=FILES/(pmid+suffix)
        filename.write_bytes(raw)
        out.update(status="EXTRACTED",method=method,
                   source_url=url,source_file=str(filename),blocks=blocks,
                   license=license_note,graphics_not_embedded=graphics)
        return out
    except Exception as exc:
        errors.append("Original free-link check: "+str(exc)[:250])
    return out

def create_word(rows, results, target):
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=sec.bottom_margin=Inches(.72)
    sec.left_margin=sec.right_margin=Inches(.8)
    style=doc.styles["Normal"]
    style.font.name="Arial"
    style.font.size=Pt(9)
    doc.add_heading("ONSM | Full-Text Research Collection",0)
    done=[r for r in rows if results[str(r["pmid"])]["status"]=="EXTRACTED"]
    missed=[r for r in rows if results[str(r["pmid"])]["status"]!="EXTRACTED"]
    doc.add_paragraph(f"Original list: {len(rows)} unique records | Complete texts retrieved: {len(done)} | Unavailable: {len(missed)}")
    doc.add_paragraph("Article wording is not translated, shortened, rewritten or supplemented with abstracts. "
                      "Formatting in Word can differ from publisher layout; equations, graphics, "
                      "PDF text reading order and embedded objects may not reproduce exactly. "
                      "Unmodified original source files are saved separately in the source ZIP.")
    for index,row in enumerate(rows,1):
        result=results[str(row["pmid"])]
        if result["status"]!="EXTRACTED":
            continue
        doc.add_page_break()
        doc.add_heading(f"{index}. {row['title']}",1)
        doc.add_paragraph("; ".join(row.get("authors") or []))
        meta=[("PMID",row["pmid"]),("DOI",row.get("doi","")),
              ("Live source",result.get("source_url","")),("Retrieval method",result.get("method","")),
              ("License statement",result.get("license",""))]
        for k,v in meta:
            if v:
                p=doc.add_paragraph()
                p.add_run(k+": ").bold=True
                p.add_run(str(v))
        for block in result.get("blocks",[]):
            kind=block["kind"]
            if kind=="table":
                rows_data=block.get("rows",[])
                if not rows_data:continue
                cols=max(len(x) for x in rows_data)
                if cols>15:
                    for tblrow in rows_data:doc.add_paragraph(" | ".join(tblrow))
                    continue
                table=doc.add_table(rows=0,cols=cols)
                table.style="Table Grid"
                for tblrow in rows_data:
                    cells=table.add_row().cells
                    for j,value in enumerate(tblrow):cells[j].text=value
                doc.add_paragraph()
            elif kind=="h":
                doc.add_heading(block.get("text",""),2)
            elif kind=="p":
                doc.add_paragraph(block.get("text",""))
        log(f"Word: {index}/{len(rows)} PMID {row['pmid']}")
    if missed:
        doc.add_page_break()
        doc.add_heading("Sources not retrieved in full — not replaced by abstracts",1)
        for row in missed:
            r=results[str(row["pmid"])]
            doc.add_paragraph(f"PMID {row['pmid']} | {row['title']}")
            doc.add_paragraph(" | ".join(r.get("errors") or ["Unknown retrieval issue"]))
    doc.save(target)

def create_audit_html(rows, results, target):
    from html import escape
    header='''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ONSM 108 — live full text audit</title>
<style>body{background:#f6f8fc;font:14px/1.8 Tahoma,Arial,sans-serif;margin:0;color:#17334b}
header{background:#224d78;color:white;padding:24px}main{max-width:1100px;margin:auto;padding:16px}
input{width:100%;padding:12px;border:1px solid #b9cddd;border-radius:8px;box-sizing:border-box}
article{background:white;border-radius:11px;border:1px solid #e0e6ef;padding:14px;margin:12px 0}
article h3{direction:ltr;text-align:left}a{color:#135c9e;overflow-wrap:anywhere}
.bad{border-right:5px solid #b66718}.ok{border-right:5px solid #238559}small{color:#5c7389}
</style></head><body><header><h1>ONSM — گزارش زنده دریافت متن کامل</h1>
<p>نتایج بررسی همان ۱۰۸ مقاله؛ نسخه‌های ناموفق به‌جای متن کامل گزارش شده‌اند.</p></header><main>
<input id="q" placeholder="جستجو..." oninput="filter()"><div id="list">'''
    cards=[]
    for row in rows:
        r=results[str(row["pmid"])]
        okay=r["status"]=="EXTRACTED"
        name=escape(str(row["title"]))
        pmid=escape(str(row["pmid"]))
        doi=escape(str(row.get("doi","")))
        reason=escape(" | ".join(r.get("errors") or []))
        source=escape(r.get("source_url") or row.get("free_url") or "")
        cards.append(
            f'<article class="{"ok" if okay else "bad"}"><h3>{name}</h3>'
            f'<b>PMID:</b> {pmid} | <b>DOI:</b> {doi}<br>'
            f'<b>نتیجه:</b> {"متن کامل دریافت شد" if okay else "دریافت متن کامل ناموفق بود"}'
            f' | <b>روش:</b> {escape(r.get("method") or "none")}<br>'
            f'<b>متن اصلی:</b> <a href="{source}" target="_blank">{source}</a><br>'
            f'<small>{reason}</small></article>'
        )
    footer='''</div></main><script>function filter(){const q=document.getElementById('q').value.toLowerCase();
for(const e of document.querySelectorAll('article'))e.hidden=!e.textContent.toLowerCase().includes(q);}</script></body></html>'''
    Path(target).write_text(header+"\n".join(cards)+footer,encoding="utf-8")

def save_audit(rows, results, prefix):
    json_path=Path(prefix+".json")
    json_path.write_text(json.dumps({
        "generated":ts(),"input_count":len(rows),
        "results":[{k:v for k,v in results[str(row["pmid"])].items() if k!="blocks"}
                   for row in rows]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    with Path(prefix+".csv").open("w",encoding="utf-8-sig",newline="") as f:
        out=csv.writer(f)
        out.writerow(["pmid","title","status","method","source_url","source_file","errors","license","checked_at"])
        for row in rows:
            r=results[str(row["pmid"])]
            out.writerow([row["pmid"],row["title"],r["status"],r.get("method",""),
                          r.get("source_url",""),r.get("source_file",""),
                          " | ".join(r.get("errors") or []),r.get("license",""),r.get("checked_at","")])

def make_sources_archive():
    path="ONSM_108_Unmodified_Originals.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
        for item in sorted(FILES.iterdir()):
            if item.is_file(): zf.write(item,"original_sources/"+item.name)
    return path

def self_test():
    fixture=b'''<article><front><article-meta><abstract><p>Abstract is not a replacement.</p></abstract></article-meta></front>
<body><sec><title>Methods</title><p>First <italic>exact</italic> text paragraph.</p></sec>
<sec><title>Results</title><p>Second paragraph with punctuation, references [1] and 4.2.</p>
<table-wrap><label>Table 1</label><table><tr><th>A</th><th>B</th></tr>
<tr><td>1</td><td>2</td></tr></table></table-wrap></sec>
<sec><title>Discussion</title><p>Long enough for parser testing. </p>
<p>''' + b'A sample sentence with readable content. '*24 + b'''</p></sec></body>
<back><ref-list><title>References</title><ref><mixed-citation>Author A. 2025.</mixed-citation></ref></ref-list></back></article>'''
    blocks,license,graphics=parse_jats(fixture)
    assert any(x.get("kind")=="table" for x in blocks)
    assert any("First exact text" in x.get("text","") for x in blocks)
    assert any("Author A." in x.get("text","") for x in blocks)
    assert not any("empty" in x.get("text","") for x in blocks)
    log("Self-test passed: JATS paragraphs, references and table parsed.")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",default="ONSM_Free_108_Articles.html")
    ap.add_argument("--output",default="ONSM_108_Full_Texts.docx")
    ap.add_argument("--auto-download",action="store_true",help="Trigger Colab download for Word and live-status HTML.")
    ap.add_argument("--retry-failed",action="store_true",help="Retry failed checkpoint records.")
    ap.add_argument("--self-test",action="store_true",help="Offline parser self-test, no network.")
    ap.add_argument("--delay",type=float,default=.35,help="Delay between articles to avoid API overload.")
    args=ap.parse_args()
    if args.self_test:
        self_test()
        return
    rows=load_input(args.input)
    FILES.mkdir(parents=True,exist_ok=True)
    RECORDS.mkdir(parents=True,exist_ok=True)
    results={}
    for index,row in enumerate(rows,1):
        pmid=str(row["pmid"])
        cache=RECORDS/(pmid+".json")
        if cache.exists():
            try:
                old=json.loads(cache.read_text(encoding="utf-8"))
                if old.get("status")=="EXTRACTED" or (old.get("status")=="FAILED" and not args.retry_failed):
                    results[pmid]=old
                    log(f"[{index}/108] PMID {pmid} — reused checkpoint ({old['status']})")
                    continue
            except (ValueError,OSError):
                pass
        log(f"[{index}/108] Live checking PMID {pmid} : {row['title'][:65]}")
        try:
            result=run_one(row)
        except Exception as exc:
            result={"pmid":pmid,"title":row["title"],"status":"FAILED","blocks":[],
                    "errors":[str(exc)],"checked_at":ts(),"source_url":"","method":""}
        results[pmid]=result
        cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        log(f"          -> {result['status']} via {result.get('method','none')}")
        time.sleep(max(0,min(args.delay,15)))
    create_word(rows,results,args.output)
    create_audit_html(rows,results,"ONSM_108_Live_Status.html")
    save_audit(rows,results,"ONSM_108_Extraction_Report")
    archives=make_sources_archive()
    n=sum(r["status"]=="EXTRACTED" for r in results.values())
    log(f"COMPLETE: {n}/108 entire texts extracted; {108-n} unavailable. Nothing substituted.")
    log(f"Word: {args.output} | Live HTML: ONSM_108_Live_Status.html")
    log("CSV/JSON audit: ONSM_108_Extraction_Report.*")
    log("Unmodified sources: "+archives)
    result_zip="ONSM_108_Results.zip"
    with zipfile.ZipFile(result_zip,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
        for name in (args.output,"ONSM_108_Live_Status.html",
                     "ONSM_108_Extraction_Report.csv","ONSM_108_Extraction_Report.json"):
            zf.write(name,arcname=Path(name).name)
    log("Consolidated results for one-click download: "+result_zip)
    if args.auto_download:
        try:
            from google.colab import files as colab_files
            colab_files.download(result_zip)
        except ImportError:
            log("Not running in Google Colab: files are in the current working folder.")

if __name__=="__main__":
    main()
