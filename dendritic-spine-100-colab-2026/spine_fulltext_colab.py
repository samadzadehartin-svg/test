#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dendritic Spine Literature — official open-full-text collector for Google Colab.

UPLOAD TO THE SAME COLAB FOLDER:
  1. spine_fulltext_colab.py
  2. spine_100_articles.json

RUN THIS ONE LINE IN A GOOGLE COLAB CELL:
  %run /content/spine_fulltext_colab.py

The script retrieves openly accessible full-text article XML from Europe PMC,
then tries the official NCBI PMC Open Access BioC service. It does NOT bypass
paywalls and NEVER mislabels an abstract as full text. It compiles a DOCX,
searchable HTML, individual text files, a CSV audit, and a ZIP archive.

Source APIs: Europe PMC REST https://www.ebi.ac.uk/europepmc/webservices/rest/
             NCBI BioC-PMC  https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/

Usage outside Colab:
  python spine_fulltext_colab.py --input spine_100_articles.json --out output_spine100
  python spine_fulltext_colab.py --workers 2 --no-auto-download
"""

import os
import sys
import re
import csv
import json
import time
import html
import zipfile
import logging
import subprocess
import argparse
import threading
import unicodedata
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


def ensure_deps():
    needed = [('requests', 'requests'), ('lxml', 'lxml'), ('docx', 'python-docx')]
    missing = [pip for mod, pip in needed if __import__('importlib').util.find_spec(mod) is None]
    if missing:
        print('Installing missing packages:', ', '.join(missing), flush=True)
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *missing])

ensure_deps()
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

EUROPE = 'https://www.ebi.ac.uk/europepmc/webservices/rest'
BIOC = 'https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json'
USER_AGENT = 'SpineDendriticAcademicFulltextCollector/1.1 (open-access research; official public APIs)'
LOCAL = threading.local()
LOG = logging.getLogger('spine100')


def get_session():
    if not hasattr(LOCAL, 'session'):
        s = requests.Session()
        r = Retry(total=4, connect=3, read=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=['GET'], respect_retry_after_header=True)
        ad = HTTPAdapter(max_retries=r, pool_connections=4, pool_maxsize=4)
        s.mount('https://', ad)
        s.headers.update({'User-Agent': USER_AGENT})
        LOCAL.session = s
    return LOCAL.session


def req(url, params=None, json_expected=False):
    # Fail fast on missing documents (404/403). Transient errors are retried.
    r = get_session().get(url, params=params, timeout=(12, 50))
    if r.status_code in (403, 404, 410):
        return None, r.url
    r.raise_for_status()
    if not r.content:
        return None, r.url
    if json_expected:
        try:
            return r.json(), r.url
        except ValueError:
            return None, r.url
    return r.content, r.url


def normalize(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def local_tag(el):
    tag = getattr(el, 'tag', '')
    return tag.rsplit('}', 1)[-1].lower() if isinstance(tag, str) else ''


def as_text(el):
    if el is None:
        return ''
    return normalize(''.join(el.itertext()))


def first_child(node, label):
    if node is None:
        return None
    return next((x for x in node if local_tag(x) == label), None)


def direct_children(node, label):
    return [x for x in node if local_tag(x) == label]


def get_abstract_meta(record):
    s = record.get('abstractText', '') or ''
    if not s:
        return ''
    return normalize(re.sub(r'<[^>]+>', ' ', html.unescape(s)))


def epmc_metadata(pmid):
    url = EUROPE + '/search'
    obj, _ = req(url, params={'query': f'EXT_ID:{pmid} AND SRC:MED',
                                'format': 'json', 'resultType': 'core', 'pageSize': '3'},
                 json_expected=True)
    results = (obj or {}).get('resultList', {}).get('result', [])
    for a in results:
        if str(a.get('pmid', a.get('id', ''))) == str(pmid):
            return a
    # Sometimes a record is still missing from MED. Do not match by title.
    obj, _ = req(url, params={'query': f'EXT_ID:{pmid}', 'format': 'json',
                              'resultType': 'core', 'pageSize': '5'}, json_expected=True)
    results = (obj or {}).get('resultList', {}).get('result', [])
    for a in results:
        if str(a.get('pmid', a.get('id', ''))) == str(pmid):
            return a
    return {}


def jats_parse(raw):
    parser = etree.XMLParser(resolve_entities=False, no_network=True,
                             recover=True, huge_tree=True, remove_comments=True)
    root = etree.fromstring(raw, parser=parser)
    if local_tag(root) == 'pmc-articleset':
        root = next((x for x in root if local_tag(x) == 'article'), root)
    if local_tag(root) != 'article':
        raise ValueError('Response is not a JATS article')

    front = first_child(root, 'front')
    article_meta = first_child(front, 'article-meta') if front is not None else None
    body = first_child(root, 'body')
    if body is None:
        raise ValueError('No article body available')
    journal_meta = first_child(front, 'journal-meta') if front is not None else None
    actual_title = ''
    if article_meta is not None:
        tg = first_child(article_meta, 'title-group')
        actual_title = as_text(first_child(tg, 'article-title'))
    license_el = next((x for x in article_meta.iter() if local_tag(x) == 'license'), None) if article_meta is not None else None
    license_txt = as_text(license_el)[:650] if license_el is not None else ''
    license_url = ''
    if license_el is not None:
        for key, val in license_el.attrib.items():
            if key.lower().endswith('href'):
                license_url = val
                break
    blocks = []

    def add(kind, content, level=0):
        content = normalize(content)
        if content and (not blocks or blocks[-1]['kind'] != kind or blocks[-1]['text'] != content):
            blocks.append({'kind': kind, 'text': content, 'level': min(level, 5)})

    def extract_table(table):
        if table is None:
            return
        for row in table.iter():
            if local_tag(row) != 'tr':
                continue
            cells = [as_text(c) for c in row if local_tag(c) in ('th', 'td')]
            if any(cells):
                add('table_row', '  |  '.join(cells))

    def walk(el, level=0):
        name = local_tag(el)
        if name in ('sec', 'app', 'ack', 'glossary', 'notes', 'boxed-text'):
            heading = first_child(el, 'title')
            if heading is not None:
                add('heading', as_text(heading), max(1, level))
            for child in el:
                if child is not heading:
                    walk(child, level+1)
        elif name == 'p':
            add('paragraph', as_text(el))
        elif name == 'list':
            for li in el:
                if local_tag(li) == 'list-item':
                    add('bullet', as_text(li))
                else:
                    walk(li, level)
        elif name == 'fig':
            label = as_text(first_child(el, 'label'))
            caption = as_text(first_child(el, 'caption'))
            if label or caption:
                add('caption', ' '.join([p for p in (label, caption) if p]))
        elif name == 'table-wrap':
            label = as_text(first_child(el, 'label'))
            caption = as_text(first_child(el, 'caption'))
            add('caption', ' '.join([x for x in (label, caption) if x]) or 'Table')
            table = next((c for c in el.iter() if local_tag(c) == 'table'), None)
            extract_table(table)
            for item in el:
                if local_tag(item) in ('table-wrap-foot', 'fn-group'):
                    add('paragraph', as_text(item))
        elif name in ('disp-formula', 'inline-formula'):
            add('formula', as_text(el))
        elif name == 'disp-quote':
            add('quotation', as_text(el))
        elif name == 'ref-list':
            add('heading', 'References', 1)
            for x in el.iter():
                if local_tag(x) == 'ref':
                    add('reference', as_text(x))
        elif name == 'abstract':
            add('heading', 'Abstract', 1)
            for x in el:
                if local_tag(x) == 'title':
                    continue
                walk(x, 1)
        elif name == 'title':
            pass
        elif name in ('supplementary-material', 'supplementary-materials'):
            add('caption', 'Supplementary material (textual description): ' + as_text(el)[:1600])
        elif name in ('graphic', 'inline-graphic', 'media', 'alternatives', 'tex-math'):
            pass  # Figure files and media binaries are not embedded in text-only output.
        else:
            for c in el:
                walk(c, level)

    if article_meta is not None:
        for ab in direct_children(article_meta, 'abstract'):
            walk(ab)
        for ab in direct_children(article_meta, 'trans-abstract'):
            walk(ab)
    add('heading', 'Main text', 1)
    walk(body)
    back = first_child(root, 'back')
    if back is not None:
        walk(back)
    main_text = [b for b in blocks if b['kind'] in ('paragraph', 'bullet')]
    main_chars = sum(len(b['text']) for b in main_text)
    if main_chars < 900 or len(main_text) < 3:
        raise ValueError('XML does not contain substantial full text')
    return {'blocks': blocks, 'article_title': actual_title,
            'license': license_txt, 'license_url': license_url,
            'body_chars': main_chars}


def bioc_parse(data):
    if not isinstance(data, (list, dict)):
        raise ValueError('Invalid BioC JSON')
    collections = data if isinstance(data, list) else [data]
    documents = []
    for coll in collections:
        if isinstance(coll, dict):
            documents += coll.get('documents', [])
    if not documents:
        raise ValueError('No BioC documents')
    blocks = []
    main_sections = 0
    text_chars = 0
    for doc in documents[:1]:
        for p in doc.get('passages', []):
            text = normalize(p.get('text'))
            if not text:
                continue
            typ = p.get('infons', {}) or {}
            section = normalize(typ.get('section_type') or typ.get('type') or '')
            sl = section.upper()
            if sl in ('TITLE', 'ABSTRACT_TITLE', 'FRONT', 'ARTICLE-TITLE'):
                continue
            if sl in ('ABSTRACT', 'ABSTRACT_PARAGRAPH'):
                kind = 'abstract'
            elif any(k in sl for k in ('TITLE', 'HEADING', 'SECTION')):
                kind = 'heading'
            elif 'REF' in sl:
                kind = 'reference'
            elif 'TABLE' in sl:
                kind = 'table_row'
            elif 'FIG' in sl:
                kind = 'caption'
            else:
                kind = 'paragraph'
                main_sections += 1
            blocks.append({'kind': kind, 'text': text, 'level': 2})
            if kind in ('paragraph', 'table_row'):
                text_chars += len(text)
    if text_chars < 900 or main_sections < 3:
        raise ValueError('BioC response appears to be abstract-only or incomplete')
    return {'blocks': blocks, 'article_title': '', 'license': '',
            'license_url': '', 'body_chars': text_chars}


def highlighted_passages(blocks):
    """Two distinct verbatim, algorithmically ranked source paragraphs; no invention."""
    terms = [('dendritic spines', 9), ('dendritic spine', 9), ('spine density', 10),
             ('spine morphology', 10), ('spine maturation', 7), ('thin spine', 8),
             ('suicide', 7), ('postmortem', 6), ('post-mortem', 6),
             ('depressive', 5), ('depression', 5), ('synaptic plasticity', 3),
             ('synapse', 3), ('prefrontal cortex', 3), ('hippocampus', 3),
             ('nucleus accumbens', 3), ('bdnf', 2), ('stress', 2)]
    ranked = []
    current = ''
    for b in blocks:
        if b['kind'] == 'heading':
            current = b['text']
        if b['kind'] != 'paragraph':
            continue
        s = b['text']
        if len(s) < 90 or len(s) > 3000:
            continue
        low = s.lower()
        score = sum(w * (1 if v in low else 0) for v, w in terms)
        # Avoid introduction-only generic passages when possible.
        if any(k in current.lower() for k in ('result', 'discussion', 'finding')):
            score += 6
        if len(s) >= 220:
            score += 3
        if score >= 12:
            ranked.append((score, current, s))
    ranked.sort(key=lambda x: -x[0])
    seen = set()
    output = []
    for score, section, s in ranked:
        if s in seen:
            continue
        output.append({'section': section, 'text': s, 'score': score})
        seen.add(s)
        if len(output) >= 2:
            break
    return output


def save_cache(pmid, output_folder, result):
    folder = output_folder / 'cache_success'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{pmid}.json'
    tmp = folder / f'{pmid}.json.tmp'
    tmp.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    tmp.replace(target)


def process_one(article, output_folder):
    pmid = str(article['pmid'])
    p = output_folder / 'cache_success' / f'{pmid}.json'
    if p.exists():
        try:
            cached = json.loads(p.read_text(encoding='utf-8'))
            if cached.get('status') == 'FULL_TEXT' and len(cached.get('blocks', [])) >= 3:
                cached['resumed'] = True
                return cached
        except Exception:
            pass
    item = dict(article)
    item.update({'status': 'NOT_AVAILABLE', 'pmcid': '', 'source': '',
                 'source_url': '', 'is_open_access': '', 'license': '',
                 'license_url': '', 'body_chars': 0, 'blocks': [],
                 'highlights': [], 'abstract_only': '', 'error': '',
                 'retrieved_utc': datetime.now(timezone.utc).isoformat()})
    errors = []
    metadata = {}
    try:
        metadata = epmc_metadata(pmid)
        item['pmcid'] = metadata.get('pmcid') or ''
        item['is_open_access'] = metadata.get('isOpenAccess') or ''
        item['abstract_only'] = get_abstract_meta(metadata)
    except Exception as e:
        errors.append('Europe PMC metadata: ' + str(e)[:180])

    pmcid = item['pmcid']
    if pmcid:
        try:
            payload, url = req(EUROPE + '/' + pmcid + '/fullTextXML')
            if payload:
                parsed = jats_parse(payload)
                item.update(parsed)
                item.update({'source': 'Europe PMC / JATS XML', 'source_url': url,
                             'status': 'FULL_TEXT'})
                # Original source preserved for audit and future use (not in ZIP by default).
                rawdir = output_folder / 'source_xml'
                rawdir.mkdir(parents=True, exist_ok=True)
                (rawdir / (pmcid + '.xml')).write_bytes(payload)
        except Exception as e:
            errors.append('JATS: ' + str(e)[:180])

    if item['status'] != 'FULL_TEXT':
        # BioC endpoint accepts PMID too; useful when PMCID mapping is unavailable.
        candidate_ids = list(dict.fromkeys([x for x in (pmcid, pmid) if x]))
        for candidate in candidate_ids:
            try:
                data, url = req(BIOC + '/' + candidate + '/unicode', json_expected=True)
                if not data:
                    continue
                parsed = bioc_parse(data)
                item.update(parsed)
                item.update({'status': 'FULL_TEXT', 'source': 'NCBI PMC OA / BioC',
                             'source_url': url})
                break
            except Exception as e:
                errors.append('BioC ' + candidate + ': ' + str(e)[:150])

    if item['status'] == 'FULL_TEXT':
        item['highlights'] = highlighted_passages(item.get('blocks') or [])
        save_cache(pmid, output_folder, item)
    item['error'] = ' | '.join(errors)[:700]
    return item


def set_doc_style(doc):
    sec = doc.sections[0]
    sec.top_margin = Inches(.82)
    sec.bottom_margin = Inches(.76)
    sec.left_margin = Inches(.8)
    sec.right_margin = Inches(.8)
    st = doc.styles['Normal']
    st.font.name = 'Calibri'
    st.font.size = Pt(10)
    st.paragraph_format.space_after = Pt(6)
    for name, size in [('Title', 21), ('Heading 1', 14), ('Heading 2', 12), ('Heading 3', 11)]:
        style = doc.styles[name]
        style.font.name = 'Calibri'
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(24, 60, 88)


def write_docx(records, folder):
    target = folder / 'Spine_100_FULLTEXT_Collected.docx'
    doc = Document()
    set_doc_style(doc)
    doc.add_heading('Dendritic Spine Alterations in Depression and Suicidal Behavior', 0)
    doc.add_paragraph('Automated online retrieval of 100 specified papers — Europe PMC and NCBI PMC OA official APIs')
    done = sum(r['status'] == 'FULL_TEXT' for r in records)
    doc.add_paragraph(f'Full texts retrieved: {done}/100  |  Unavailable: {100-done}  |  Created UTC: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}')
    doc.add_paragraph('IMPORTANT: Only articles with a FULL_TEXT status have their article body retrieved. Unavailable articles display bibliographic information and, when available, a separately labeled abstract — NEVER a fabricated full text. Figure binaries and supplementary attachments are not embedded. Source texts are reproduced from APIs and are subject to the respective article license.')
    last_section = None
    for a in records:
        if last_section != a['section']:
            last_section = a['section']
            doc.add_heading(last_section, 1)
        doc.add_heading(f"{int(a['number']):03d}. {a['title']}", 2)
        doc.add_paragraph('Citation: ' + a.get('reference', ''))
        doc.add_paragraph(f"PMID: {a['pmid']}  |  PMCID: {a.get('pmcid') or 'N/A'}  |  DOI: {a.get('doi') or 'N/A'}")
        doc.add_paragraph(f"PubMed: https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/")
        if a.get('doi'):
            doc.add_paragraph('DOI URL: https://doi.org/' + a['doi'])
        status = a.get('status')
        doc.add_paragraph(f"Retrieval status: {status}  |  Source: {a.get('source') or 'not available'}  |  Public OA flag: {a.get('is_open_access') or 'unknown'}")
        if a.get('source_url'):
            doc.add_paragraph('Full-text source: ' + a['source_url'])
        if a.get('license') or a.get('license_url'):
            doc.add_paragraph('License / reuse note: ' + (a.get('license') or '') + ' ' + (a.get('license_url') or ''))
        if status == 'FULL_TEXT':
            if a.get('highlights'):
                doc.add_heading('Candidate paragraphs (VERBATIM from fetched source; verify before using)', 3)
                for n, p in enumerate(a['highlights'], 1):
                    doc.add_paragraph(f"{n}. Section: {p['section'] or 'unlabeled'}")
                    pp = doc.add_paragraph(p['text'])
                    pp.style = 'Quote'
            doc.add_heading('Complete accessible article text (figures/images excluded)', 3)
            for b in a.get('blocks', []):
                kind, s = b['kind'], b['text']
                if kind == 'heading':
                    doc.add_heading(s, min(4, 3 if b.get('level', 2) <= 2 else 4))
                elif kind == 'bullet':
                    doc.add_paragraph(s, style='List Bullet')
                elif kind == 'reference':
                    p = doc.add_paragraph(s)
                    p.style = 'Normal'
                elif kind == 'caption':
                    p = doc.add_paragraph(s)
                    for run in p.runs:
                        run.italic = True
                elif kind == 'table_row':
                    doc.add_paragraph(s, style='Normal')
                else:
                    doc.add_paragraph(s)
        else:
            doc.add_paragraph('FULL TEXT NOT AVAILABLE THROUGH THE OFFICIAL OPEN-FULL-TEXT SERVICES. This is not the complete article.')
            if a.get('abstract_only'):
                doc.add_heading('ABSTRACT ONLY (not full text)', 3)
                doc.add_paragraph(a['abstract_only'])
        doc.add_page_break()
    doc.save(target)
    return target


def write_html(records, folder):
    target = folder / 'Spine_100_FULLTEXT_Searchable.html'
    css = ('body{font:16px/1.7 Georgia,serif;max-width:1050px;margin:2rem auto;padding:1rem;color:#263238;}'
           'h1,h2,h3,h4{font-family:system-ui,sans-serif;color:#183c58}article{border-top:2px solid #ddd;padding:25px 0}'
           'nav a{display:block;font:14px/1.5 sans-serif;padding:4px;} .meta{background:#f2f6fb;padding:10px;border-radius:5px;font:14px/1.5 sans-serif;}'
           '.highlight{background:#fff9d5;border-left:3px solid #d5a21e;padding:10px;margin:10px 0;}'
           '.caption{font-style:italic;color:#3a5774}.tablerow{font-family:monospace;white-space:pre-wrap;overflow-wrap:anywhere;}'
           '.status{font-weight:bold}.missing{color:#942e23}.reference{font-size:13px;color:#53636f}')
    def esc(s):return html.escape(str(s or ''))
    chunks = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Spine 100 fulltext</title>',
              '<style>' + css + '</style><h1>Spine 100 — retrieved open full texts</h1>',
              '<p>Created UTC ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M') +
              '. Missing full texts are clearly labeled; no paywalled content is bypassed.</p><nav>']
    for a in records:
        chunks.append(f'<a href="#p{a["pmid"]}">{a["number"]:03d} — {esc(a["title"])}</a>')
    chunks.append('</nav>')
    for a in records:
        chunks.append(f'<article id="p{a["pmid"]}"><h2>{a["number"]:03d}. {esc(a["title"])}</h2>')
        chunks.append(f'<div class="meta">{esc(a["reference"])}<br><b>PMID:</b> {esc(a["pmid"])} | <b>PMCID:</b> {esc(a.get("pmcid"))}'
                      f' | <b>DOI:</b> {esc(a.get("doi"))} | <span class="status">{esc(a["status"])}</span><br>'
                      f'<a href="https://pubmed.ncbi.nlm.nih.gov/{a["pmid"]}/">PubMed</a>')
        if a.get('source_url'):
            chunks.append(f' | <a href="{esc(a["source_url"])}">Retrieved full text</a>')
        chunks.append('</div>')
        if a['status'] == 'FULL_TEXT':
            if a.get('highlights'):
                chunks.append('<h3>Verbatim candidate paragraphs</h3>')
                for p in a['highlights']:
                    chunks.append('<div class="highlight"><b>' + esc(p['section']) + '</b><p>' + esc(p['text']) + '</p></div>')
            chunks.append('<h3>Full accessible text</h3>')
            for b in a.get('blocks', []):
                k, t = b['kind'], esc(b['text'])
                if k == 'heading': chunks.append('<h4>' + t + '</h4>')
                elif k == 'caption': chunks.append('<p class="caption">' + t + '</p>')
                elif k == 'table_row': chunks.append('<p class="tablerow">' + t + '</p>')
                elif k == 'reference': chunks.append('<p class="reference">' + t + '</p>')
                elif k == 'bullet': chunks.append('<p>• ' + t + '</p>')
                else: chunks.append('<p>' + t + '</p>')
        else:
            chunks.append('<p class="missing">Full text unavailable through official public full-text APIs.</p>')
            if a.get('abstract_only'):
                chunks.append('<h3>Abstract only — NOT full text</h3><p>' + esc(a['abstract_only']) + '</p>')
        chunks.append('</article>')
    chunks.append('</html>')
    target.write_text('\n'.join(chunks), encoding='utf-8')
    return target


def write_csv(records, folder):
    target = folder / 'Spine_100_Access_Audit.csv'
    keys = ['number', 'section', 'title', 'pmid', 'pmcid', 'doi', 'priority', 'category',
            'status', 'is_open_access', 'source', 'source_url', 'body_chars', 'license_url',
            'retrieved_utc', 'error']
    with target.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(records)
    return target


def write_texts(records, folder):
    path = folder / 'individual_fulltexts'
    path.mkdir(exist_ok=True)
    for a in records:
        if a['status'] != 'FULL_TEXT':
            continue
        lines = [a['title'], a['reference'], f"PMID: {a['pmid']}",
                 f"PMCID: {a.get('pmcid')}", f"Retrieved from: {a.get('source_url')}", '']
        for b in a['blocks']:
            lines.append(b['text'] + '\n')
        (path / f"{a['number']:03d}_PMID_{a['pmid']}.txt").write_text('\n'.join(lines), encoding='utf-8')
    return path


def archive_outputs(docx_path, html_path, csv_path, txtdir, folder):
    zip_path = folder / 'Spine_100_FULLTEXT_RESULTS.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as z:
        for p in [docx_path, html_path, csv_path]:
            z.write(p, p.name)
        for p in sorted(txtdir.glob('*.txt')):
            z.write(p, 'individual_fulltexts/' + p.name)
        readme = ('Spine 100 FULLTEXT retrieval package\n'
                  'All articles identified by the exact PMIDs from the uploaded reference DOCX.\n'
                  'FULL_TEXT means official Europe PMC JATS or NCBI PMC OA BioC document available.\n'
                  'NOT_AVAILABLE means no accessible full text was returned by either service;\n'
                  'it does NOT imply that the paper is unavailable everywhere.\n'
                  'Searchable HTML contains only available text; tables are flattened into rows.\n'
                  'Figure/media binaries and supplementary attachments are not included.\n'
                  'Respect article-specific Creative Commons/reuse licenses.\n')
        z.writestr('READ_ME.txt', readme)
    return zip_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=None, help='JSON with 100 PMIDs')
    parser.add_argument('--out', default=None)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--no-auto-download', action='store_true')
    args, _ = parser.parse_known_args()
    home = Path(__file__).resolve().parent
    inp = Path(args.input).resolve() if args.input else home / 'spine_100_articles.json'
    if not inp.exists():
        inp = Path.cwd() / 'spine_100_articles.json'
    if not inp.exists():
        raise FileNotFoundError('Please upload spine_100_articles.json next to this script (usually /content).')
    content = json.loads(inp.read_text(encoding='utf-8'))
    articles = content['articles'] if isinstance(content, dict) else content
    if len(articles) != 100 or len(set(a['pmid'] for a in articles)) != 100:
        raise ValueError('Input must contain exactly 100 unique PMIDs; refusing to substitute other articles.')
    outdir = Path(args.out).resolve() if args.out else home / 'Spine100_Results'
    outdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.WARNING)
    print(f'INPUT: {inp}\nARTICLES: {len(articles)}\nOUTPUT FOLDER: {outdir}', flush=True)
    print('Source: official Europe PMC JATS XML; NCBI PMC OA BioC fallback. No paywall access.', flush=True)
    outputs = {}
    workers = max(1, min(args.workers, 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_one, a, outdir): a for a in articles}
        for k, fut in enumerate(as_completed(futures), 1):
            a = futures[fut]
            try:
                result = fut.result()
            except Exception as e:
                result = dict(a, status='ERROR', pmcid='', source='', source_url='',
                              is_open_access='', license='', license_url='', body_chars=0,
                              blocks=[], highlights=[], abstract_only='', error=str(e)[:500])
            outputs[result['pmid']] = result
            print(f'[{k:03d}/100] PMID {result["pmid"]} | {result["status"]:<13} | {result.get("body_chars",0):>7} chars | {result["title"][:62]}', flush=True)
    records = [outputs[a['pmid']] for a in articles]
    print('BUILDING WORD, HTML AND AUDIT ...', flush=True)
    docx_path = write_docx(records, outdir)
    html_path = write_html(records, outdir)
    csv_path = write_csv(records, outdir)
    txtdir = write_texts(records, outdir)
    zip_path = archive_outputs(docx_path, html_path, csv_path, txtdir, outdir)
    retrieved = sum(a['status'] == 'FULL_TEXT' for a in records)
    print('\n' + '='*65, flush=True)
    print(f'FINISHED: {retrieved} full text articles / 100; {100-retrieved} not retrieved', flush=True)
    print(f'WORD : {docx_path}', flush=True)
    print(f'HTML : {html_path}', flush=True)
    print(f'CSV  : {csv_path}', flush=True)
    print(f'ZIP  : {zip_path} ({zip_path.stat().st_size:,} bytes)', flush=True)
    print('For missing articles, open the CSV audit and follow the PubMed/DOI page manually.', flush=True)
    if not args.no_auto_download and 'COLAB_RELEASE_TAG' in os.environ:
        try:
            from google.colab import files
            print('Starting Google Colab browser download ...', flush=True)
            files.download(str(zip_path))
        except Exception as e:
            print('Automatic Colab download not available:', str(e), flush=True)
            print('Download the ZIP manually using the Colab Files sidebar.', flush=True)
    return str(zip_path)


if __name__ == '__main__':
    main()