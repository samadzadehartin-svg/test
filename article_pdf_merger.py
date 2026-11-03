#!/usr/bin/env python3
"""Merge already-obtained research PDFs into one annotated, offline HTML document.

Usage (local):
  pip install pymupdf
  python article_pdf_merger.py --input /path/to/pdfs_or_zip --output Collected_Full_Texts.html

Usage (Google Colab on your personal computer, not university workstation):
  !pip -q install pymupdf
  !python article_pdf_merger.py --colab
Then upload a ZIP containing PDFs; an HTML and report ZIP will be downloaded.

This utility does NOT fetch paywalled material or bypass access restrictions.
"""
import argparse
import csv
import html
import io
import os
from pathlib import Path
import re
import tempfile
import zipfile

try:
    import fitz
except ImportError:
    raise SystemExit('PyMuPDF not installed. Run: pip install pymupdf')

CSS = '''body{font:15px/1.85 system-ui,-apple-system,Arial,sans-serif;max-width:980px;margin:35px auto;padding:0 20px;background:#f8fafc;color:#18233b}
header,.paper{background:white;border:1px solid #d9e2ef;border-radius:13px;padding:25px;margin:20px 0;box-shadow:0 4px 18px #1223470a}
h1{font-size:27px}h2{font-size:21px;margin-bottom:6px;overflow-wrap:anywhere}h3{margin:24px 0 6px;color:#3b5181}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.75 Arial,Helvetica,sans-serif;direction:ltr;text-align:left}
small,.meta{color:#5b6a80}.page{border-bottom:1px dashed #d8e1ef;padding:5px 0 15px}
a{color:#254fb4}article{break-before:page}.status{background:#fff4de;padding:9px;border-radius:6px}
@media print{body{background:white;max-width:none}.paper{box-shadow:none;border:none}article{page-break-before:always}}
'''


def pdf_entries(p):
    p = Path(p)
    if p.is_dir():
        for f in sorted(p.rglob('*.pdf')):
            yield f.name, f.read_bytes()
    elif p.suffix.lower() == '.pdf':
        yield p.name, p.read_bytes()
    elif p.suffix.lower() == '.zip':
        with zipfile.ZipFile(p) as z:
            for entry in z.infolist():
                if not entry.is_dir() and entry.filename.lower().endswith('.pdf'):
                    yield Path(entry.filename).name, z.read(entry)
    else:
        raise ValueError('Input must be a folder, .zip, or .pdf')


def merge(input_path, output_path, report_path):
    output_path, report_path = Path(output_path), Path(report_path)
    count, pages, good, failures = 0, 0, 0, 0
    with output_path.open('w', encoding='utf-8') as f, report_path.open('w', encoding='utf-8-sig', newline='') as r:
        f.write('<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Collected Research Full Texts</title><style>' + CSS + '</style></head><body>')
        f.write('<header><h1>Collected Research Full Texts</h1><p>Text extracted from research PDFs supplied by the researcher. This report is for authorized personal research use.</p><p>Extraction is not OCR. Text-based PDFs are supported; scans may have no searchable text.</p></header>')
        w = csv.writer(r)
        w.writerow(['index', 'filename', 'pages', 'chars_extracted', 'status', 'error'])
        for filename, data in pdf_entries(input_path):
            count += 1
            f.write(f'<article class="paper"><h2>#{count} — {html.escape(filename)}</h2><p class="meta">Source PDF: {html.escape(filename)}</p>')
            try:
                doc = fitz.open(stream=data, filetype='pdf')
                n_pages, num_chars = len(doc), 0
                for i in range(n_pages):
                    txt = doc[i].get_text('text', sort=True)
                    num_chars += len(txt)
                    f.write(f'<section class="page"><h3>Page {i + 1}</h3><pre>{html.escape(txt)}</pre></section>')
                doc.close()
                status = 'OK' if num_chars > 100 else 'LOW_TEXT_OR_SCANNED'
                f.write(f'<p class="meta">Extracted characters: {num_chars:,}; Pages: {n_pages}</p>')
                w.writerow([count, filename, n_pages, num_chars, status, ''])
                pages += n_pages
                if status == 'OK': good += 1
            except Exception as ex:
                failures += 1
                f.write(f'<p class="status">Could not read: {html.escape(str(ex))}</p>')
                w.writerow([count, filename, 0, 0, 'ERROR', str(ex)])
            f.write('</article>\n')
            if count % 25 == 0: print(f'Processed {count} PDFs ({pages} pages)', flush=True)
        f.write('</body></html>')
    print(f'Done: {count} PDF files, {pages} pages, {good} text-bearing, {failures} failed')
    print('Output:', output_path)
    print('Report:', report_path)
    return count


def run_colab(out_prefix):
    try:
        from google.colab import files
    except ImportError:
        raise SystemExit('--colab only works within Google Colab; otherwise use --input')
    print('Upload one ZIP of previously obtained PDFs (or one PDF).')
    uploaded = files.upload()
    if not uploaded:
        raise SystemExit('No upload provided')
    inp = next(iter(uploaded))
    html_out = Path(f'{out_prefix}.html')
    report = Path(f'{out_prefix}_extraction_report.csv')
    merge(inp, html_out, report)
    bundle = Path(f'{out_prefix}_bundle.zip')
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5, allowZip64=True) as z:
        z.write(html_out, arcname=html_out.name)
        z.write(report, arcname=report.name)
    print('Downloading:', bundle)
    files.download(str(bundle))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--input', help='A PDF, a ZIP of PDFs, or a folder containing PDFs')
    ap.add_argument('--output', default='Collected_Full_Texts.html')
    ap.add_argument('--colab', action='store_true', help='Upload PDF ZIP from Colab and download output bundle')
    args = ap.parse_args()
    if args.colab: return run_colab('Collected_Full_Texts')
    if not args.input: ap.error('--input is required without --colab')
    merge(args.input, args.output, Path(args.output).with_name(Path(args.output).stem + '_report.csv'))


if __name__ == '__main__': main()