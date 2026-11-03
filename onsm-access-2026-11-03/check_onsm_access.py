#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live full-text access checker for the complete ONSM PubMed HTML collection.
Checks Europe PMC then OpenAlex; outputs a Word report retaining EVERY occurrence.
"""
import argparse, csv, json, re, time, threading, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests
from docx import Document
from docx.shared import Inches, Pt, RGBColor

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OPENALEX = "https://api.openalex.org/works/"
STATE = threading.local()

def session():
    if not hasattr(STATE, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent":"ONSM-FullText-Availability-Research/1.0","Accept":"application/json"})
        STATE.s = s
    return STATE.s

def json_request(url, params=None, allow_404=False):
    issue = None
    for attempt in range(5):
        try:
            response = session().get(url, params=params, timeout=(12, 32))
            if allow_404 and response.status_code == 404:
                return {}, None
            if response.status_code in (429, 500, 502, 503, 504):
                issue = "HTTP " + str(response.status_code)
                retry = response.headers.get("Retry-After","")
                delay = min(30, max(2 ** attempt + 1, int(retry) if retry.isdigit() else 0))
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json(), None
        except (requests.RequestException, ValueError) as exc:
            issue = str(exc)[:180]
            time.sleep(min(20, 2 ** attempt + 1))
    return {}, issue or "Unknown server error"

def yes(value):
    return str(value).lower() in ("y","yes","true","1")

def epmc(pmid):
    data, error = json_request(EPMC, {"query":f"EXT_ID:{pmid} AND SRC:MED",
                                       "format":"json","resultType":"core","pageSize":1})
    if error:
        return {}, error
    rows = data.get("resultList",{}).get("result",[])
    if not rows:
        return {}, None
    r = rows[0]
    ji = r.get("journalInfo") or {}
    journal = ji.get("journal") or {}
    links = (r.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    free_links = [t.get("url","") for t in links if
                  ("free" in str(t.get("availability","")).lower() or
                   "open access" in str(t.get("availability","")).lower())
                  and str(t.get("url","")).startswith("http")]
    pmcid = r.get("pmcid") or ""
    in_pmc = yes(r.get("inPMC"))
    free = yes(r.get("isOpenAccess")) or in_pmc or bool(free_links)
    url = ("https://pmc.ncbi.nlm.nih.gov/articles/" + pmcid + "/"
           if in_pmc and pmcid else
           (free_links[0] if free_links else
            ("https://europepmc.org/article/MED/"+pmid if free else "")))
    return {"free":bool(free),"url":url,"pmcid":pmcid,
            "journal": journal.get("title") or journal.get("isoAbbreviation") or r.get("journalTitle") or "",
            "volume":str(ji.get("volume") or ""),
            "issue":str(ji.get("issue") or ""),
            "pages":str(r.get("pageInfo") or ""),
            "date":str(r.get("firstPublicationDate") or r.get("firstIndexDate") or ""),
            "isOpenAccess":str(r.get("isOpenAccess") or ""),
            "inPMC":str(r.get("inPMC") or "")}, None

def openalex(doi):
    if not doi:
        return {}, None
    url = OPENALEX + quote("https://doi.org/" + str(doi), safe=":/")
    data, error = json_request(url, allow_404=True)
    if error or not data:
        return {}, error
    access = data.get("open_access") or {}
    loc = data.get("best_oa_location") or {}
    free = bool(access.get("is_oa") and loc.get("is_oa", True))
    address = (loc.get("pdf_url") or loc.get("landing_page_url") or access.get("oa_url") or "") if free else ""
    primary = (data.get("primary_location") or {}).get("source") or {}
    bib = data.get("biblio") or {}
    pages = str(bib.get("first_page") or "")
    if bib.get("last_page") and pages:
        pages += "-" + str(bib.get("last_page"))
    return {"free":free,"url":address,"oa_status":access.get("oa_status") or "",
            "journal":primary.get("display_name") or "",
            "volume":str(bib.get("volume") or ""),"issue":str(bib.get("issue") or ""),
            "pages":pages}, None

def check(row):
    pmid = str(row["pmid"]).strip()
    ep, ep_error = epmc(pmid)
    if ep.get("free"):
        return {"class":"FREE","pmid":pmid,"source":"Europe PMC / PubMed Central",
                "url":ep.get("url") or "", "epmc":ep,"openalex":{},
                "errors":[ep_error] if ep_error else [],
                "checked_at":datetime.now(timezone.utc).isoformat()}
    oa, oa_error = openalex(row.get("doi") or "")
    is_free = bool(oa.get("free"))
    return {"class":"FREE" if is_free else "UNIVERSITY","pmid":pmid,
            "source":"OpenAlex" if is_free else "No verified public full text",
            "url":oa.get("url","") if is_free else "",
            "epmc":ep,"openalex":oa,
            "errors":[e for e in (ep_error,oa_error) if e],
            "checked_at":datetime.now(timezone.utc).isoformat()}

def load_html(filename):
    raw = Path(filename).read_text(encoding="utf-8-sig")
    match = re.search(r'<script\b[^>]*\bid=["\x27]dataset["\x27][^>]*>(.*?)</script\s*>',
                      raw, flags=re.I|re.S)
    if not match:
        raise ValueError("Could not find <script id='dataset'> in HTML input.")
    records = json.loads(match.group(1))["records"]
    if not records or any(not str(r.get("pmid","")).strip() for r in records):
        raise ValueError("No valid PMID records found.")
    return records

def report_docx(rows, results, target):
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(.72)
    sec.top_margin = sec.bottom_margin = Inches(.7)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9)
    normal.paragraph_format.space_after = Pt(4)
    title = doc.add_heading("ONSM — Full-Text Access Report",0)
    title.alignment = 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    doc.add_paragraph("Online check completed: " + now)
    n_unique = len(results)
    n_free = sum(x["class"] == "FREE" for x in results.values())
    doc.add_paragraph(f"Input records: {len(rows)} | Unique PMID: {n_unique} | "
                      f"Extra duplicate records: {len(rows)-n_unique}")
    doc.add_paragraph(f"Unique FREE confirmed: {n_free} | University follow-up: {n_unique-n_free}")
    doc.add_paragraph("University follow-up means that no publicly accessible full-text "
                      "copy was verified by these services; this is NOT proof that the "
                      "article is paywalled. A free author manuscript or preprint counts as FREE. "
                      "Technical API errors are included below.",style="Caption")
    doc.add_heading("Every input article (original order; duplicates retained)",1)
    counts = Counter(str(r["pmid"]) for r in rows)
    occurrences = Counter()
    def field(label, value):
        paragraph = doc.add_paragraph()
        paragraph.add_run(label+": ").bold = True
        paragraph.add_run(str(value) if value not in ("",None,[]) else "Not available in sources")
    for index,row in enumerate(rows,1):
        pmid = str(row["pmid"])
        occurrences[pmid] += 1
        answer = results[pmid]
        ep = answer.get("epmc") or {}
        oa = answer.get("openalex") or {}
        head = doc.add_heading(str(index)+". "+(row.get("title") or "Untitled"),2)
        head.paragraph_format.keep_with_next = True
        field("Authors", "; ".join(row.get("authors") or []))
        field("Journal",ep.get("journal") or oa.get("journal") or row.get("journal") or "")
        field("Published", ep.get("date") or row.get("pubdate") or row.get("year") or "")
        field("Volume / Issue / Pages", " / ".join((ep.get("volume") or oa.get("volume") or "-",
              ep.get("issue") or oa.get("issue") or "-",
              ep.get("pages") or oa.get("pages") or "-")))
        field("Publication types","; ".join(row.get("types") or []))
        field("DOI",row.get("doi") or "")
        field("PMID",pmid)
        field("PMCID",ep.get("pmcid") or "")
        field("PubMed URL","https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/")
        field("Source HTML",row.get("sourceFile") or "")
        if counts[pmid]>1:
            field("Occurrence",f"{occurrences[pmid]} of {counts[pmid]}")
        status = ("رایگان — دسترسی به متن کامل آزاد تأیید شد" if answer["class"]=="FREE"
                  else "نیازمند پیگیری دانشگاهی — دسترسی رایگان تأیید نشد")
        paragraph = doc.add_paragraph()
        run = paragraph.add_run("وضعیت متن کامل: "+status)
        run.bold = True
        run.font.color.rgb = (RGBColor(23,113,58) if answer["class"]=="FREE"
                              else RGBColor(147,81,14))
        field("Evidence source",answer.get("source") or "")
        if answer.get("url"):
            field("Free full-text URL",answer["url"])
        if answer.get("errors"):
            field("Technical errors / manual recheck needed",
                  " | ".join(answer["errors"]))
        if index<len(rows):
            doc.add_paragraph("─"*30)
        if index%25==0:
            print(f"Writing Word records: {index}/{len(rows)}",flush=True)
    doc.save(target)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",default="ONSM_all_536.html")
    p.add_argument("--output",default="ONSM_Access_Report.docx")
    p.add_argument("--workers",type=int,default=4)
    p.add_argument("--checkpoint",default="ONSM_Access_Checkpoint.json")
    p.add_argument("--resume",action="store_true",
                   help="Resume an interrupted run using checkpoint (skip earlier results).")
    p.add_argument("--no-download",action="store_true",
                   help="Disable automatic Google Colab Word download.")
    args = p.parse_args()
    rows = load_html(args.input)
    unique = {}
    for row in rows:
        unique.setdefault(str(row["pmid"]),row)
    print(f"Loaded {len(rows)} records, {len(unique)} unique PMIDs.",flush=True)
    cache = {}
    checkpoint = Path(args.checkpoint)
    if args.resume and checkpoint.is_file():
        try:
            prev = json.loads(checkpoint.read_text(encoding="utf-8"))
            cache = {key:val for key,val in prev.items()
                     if key in unique and isinstance(val,dict)
                     and val.get("class") in ("FREE","UNIVERSITY")}
        except (ValueError,OSError):
            pass
    needed = [row for key,row in unique.items() if key not in cache]
    print(f"Checking {len(needed)} live records with {max(1,min(8,args.workers))} workers.",flush=True)
    with ThreadPoolExecutor(max_workers=max(1,min(8,args.workers))) as ex:
        futures = {ex.submit(check,row):str(row["pmid"]) for row in needed}
        for i,future in enumerate(as_completed(futures),1):
            pmid = futures[future]
            try:
                cache[pmid] = future.result()
            except Exception as error:
                cache[pmid] = {"class":"UNIVERSITY","pmid":pmid,"source":"Online verification error",
                               "url":"","epmc":{},"openalex":{},
                               "errors":[str(error)[:200]],
                               "checked_at":datetime.now(timezone.utc).isoformat()}
            checkpoint.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"[{i}/{len(needed)}] PMID={pmid} {cache[pmid]['class']}"
                  +(" WARNING" if cache[pmid].get("errors") else ""),flush=True)
    output = Path(args.output)
    report_docx(rows,cache,output)
    audit = output.with_suffix(".json")
    audit.write_text(json.dumps({"records":rows,"results_by_pmid":cache},
                                ensure_ascii=False,indent=2),encoding="utf-8")
    tabular = output.with_suffix(".csv")
    with tabular.open("w",newline="",encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["row","pmid","title","doi","classification","free_url","source","errors"])
        for index,row in enumerate(rows,1):
            value = cache[str(row["pmid"])]
            writer.writerow([index,row["pmid"],row.get("title",""),row.get("doi",""),
                             value["class"],value.get("url",""),value.get("source",""),
                             " | ".join(value.get("errors",[]))])
    print(f"Word completed: {output} ({output.stat().st_size:,} bytes)",flush=True)
    print(f"Audit copies: {audit} and {tabular}",flush=True)
    if not args.no_download:
        try:
            from google.colab import files
            files.download(str(output))
        except ImportError:
            pass

if __name__=="__main__":
    main()
