#!/usr/bin/env python3
"""Resilient 100-paper Word builder for Google Colab.

Downloads the *existing* curated GitHub ZIP, obtains PubMed/Europe PMC data
when available, never fails the whole job because of temporary HTTP errors,
and labels exact licensed text, abstracts and provisional summaries separately.
"""
import csv, io, json, os, re, subprocess, sys, time, zipfile
from urllib.parse import urlsplit
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', '-q', 'install', 'requests'])
    import requests
try:
    from docx import Document
    from docx.shared import Inches, Pt
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', '-q', 'install', 'python-docx'])
    from docx import Document
    from docx.shared import Inches, Pt

RAW = ('https://raw.githubusercontent.com/samadzadehartin-svg/test/'
       'research-colab-100-papers-20261103/Environmental_Behavioral_100_Colab_GitHub.zip')
GITHUB_ALT = RAW.replace('https://raw.githubusercontent.com/samadzadehartin-svg/test/',
                         'https://github.com/samadzadehartin-svg/test/raw/')
RAW_CSV = ('https://raw.githubusercontent.com/samadzadehartin-svg/test/'
           'research-colab-100-papers-20261103/curated_100_metadata.csv')
OUTPUT = 'Environmental_Behavioral_Lifestyle_100_Research_Evidence.docx'
CACHE = Path('paper_cache_100'); CACHE.mkdir(exist_ok=True)
SESSION = requests.Session()
HOST_ERRORS = {}
HOST_COOLDOWN = {}
SESSION.headers.update({'User-Agent': 'AcademicLiteratureResearch/2.0 (Google Colab academic evidence review)',
                        'Accept': 'application/json, application/xml, text/xml, */*'})


def safe_request(url, params=None, attempts=3, binary=False):
    """A bad paper or 429/500/502/503/504 is a warning, not a fatal error."""
    host = urlsplit(url).hostname or ''
    if time.time() < HOST_COOLDOWN.get(host, 0):
        return None  # prevent a failing server from stalling all 100 articles
    for i in range(attempts):
        try:
            res = SESSION.get(url, params=params, timeout=(8, 22), allow_redirects=True)
            if res.status_code == 200:
                HOST_ERRORS[host] = 0
                return res.content if binary else res.text
            if res.status_code in (400, 401, 403, 404, 410):
                print('  [source unavailable]', res.status_code, url[:105], flush=True)
                return None
            wait = min(12, 2 ** i + 1)
            print('  [temporary HTTP error]', res.status_code, 'retry', i + 1, flush=True)
        except requests.RequestException as ex:
            wait = min(12, 2 ** i + 1)
            print('  [network warning]', str(ex)[:140], flush=True)
        if i + 1 < attempts:
            time.sleep(wait)
    HOST_ERRORS[host] = HOST_ERRORS.get(host, 0) + 1
    if HOST_ERRORS[host] >= 2 and host not in ('github.com', 'raw.githubusercontent.com'):
        HOST_COOLDOWN[host] = time.time() + 600
        print('  [circuit breaker] Temporarily skipping unresponsive server:', host, flush=True)
    return None


def input_rows():
    options = [Path('papers.csv'), Path('Environmental_Behavioral_Lifestyle_100_Papers.csv')]
    if not any(p.exists() for p in options):
        curated = safe_request(RAW_CSV)
        if curated and 'PMID' in curated[:300]:
            options[1].write_text(curated, encoding='utf-8')
        else:
            data = safe_request(RAW, binary=True) or safe_request(GITHUB_ALT, binary=True)
            if not data:
                raise RuntimeError('GitHub could not be reached. Upload the original ZIP or CSV using Colab Files and rerun.')
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    z.extractall('.')
            except zipfile.BadZipFile:
                raise RuntimeError('The downloaded ZIP was invalid. Download it in Chrome and upload it to Colab Files.')
    file = next((p for p in options if p.exists()), None)
    if not file:
        raise RuntimeError('papers.csv is missing from the archive.')
    with file.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise RuntimeError('Input CSV is empty.')
    def pick(rec, *needles):
        for n in needles:
            for k, v in rec.items():
                if k and k.lower().strip() == n.lower() and v: return str(v).strip()
        return ''
    result = []
    for r in rows:
        pmid = pick(r, 'PMID', 'pubmed_id', 'pubmed id', 'id')
        if not re.fullmatch(r'\d{6,9}', pmid):
            continue
        result.append({'pmid': pmid,
                       'title': pick(r, 'Title', 'article_title'),
                       'section': pick(r, 'Section', 'Category', 'Subtopic', 'Topic'),
                       'authors': pick(r, 'Authors', 'Author'),
                       'year': pick(r, 'Year'),
                       'journal': pick(r, 'Journal'),
                       'doi': pick(r, 'DOI'),
                       'summary': pick(r, 'Original paraphrase', 'summary', 'Evidence', 'abstract')})
    seen = set(); result = [r for r in result if not (r['pmid'] in seen or seen.add(r['pmid']))]
    print('Loaded', len(result), 'unique PubMed records.', flush=True)
    if len(result) != 100:
        print('WARNING: expected 100, got', len(result), '; continuing with verified IDs.', flush=True)
    return result


def text_from(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def metadata(pmid):
    path = CACHE / f'{pmid}_meta.json'
    if path.exists():
        try: return json.loads(path.read_text('utf-8'))
        except (ValueError, OSError): pass
    params = {'query': f'EXT_ID:{pmid} AND SRC:MED', 'format': 'json', 'pageSize': '1'}
    raw = safe_request('https://www.ebi.ac.uk/europepmc/webservices/rest/search', params=params)
    if raw:
        try:
            records = json.loads(raw).get('resultList', {}).get('result', [])
            if records:
                value = records[0]
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                return value
        except (ValueError, KeyError): pass
    # E-utilities is a fallback: individual server failures must not stop Word creation.
    raw = safe_request('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
                       {'db': 'pubmed', 'id': pmid, 'retmode': 'json', 'tool': 'colab_evidence_review'})
    if raw:
        try:
            obj = json.loads(raw).get('result', {}).get(pmid, {})
            if obj:
                value = {'title': obj.get('title', ''), 'authorString': ', '.join(x.get('name', '') for x in obj.get('authors', [])),
                         'journalTitle': obj.get('fulljournalname', ''), 'pubYear': str(obj.get('pubdate', ''))[:4],
                         'doi': next((x.get('value') for x in obj.get('articleids', []) if x.get('idtype') == 'doi'), ''),
                         'pmcid': next((x.get('value') for x in obj.get('articleids', []) if x.get('idtype') == 'pmc'), '')}
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                return value
        except (ValueError, KeyError, TypeError): pass
    return {}


def article_abstract(pmid):
    path = CACHE / f'{pmid}_abstract.txt'
    if path.exists(): return path.read_text('utf-8')
    raw = safe_request('https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                       {'query': f'EXT_ID:{pmid} AND SRC:MED', 'format': 'json', 'resultType': 'core', 'pageSize': 1})
    if raw:
        try:
            result = json.loads(raw).get('resultList', {}).get('result', [])
            abstract = re.sub(r'<[^>]+>', ' ', result[0].get('abstractText', '')).strip() if result else ''
            if abstract:
                path.write_text(abstract, encoding='utf-8')
                return abstract
        except (ValueError, TypeError, KeyError): pass
    return ''


def licensed_fulltext_paragraph(pmcid, section):
    if not pmcid or not re.fullmatch(r'PMC\d+', pmcid): return '', 'No PMCID'
    path = CACHE / (pmcid + '.xml')
    raw = path.read_text('utf-8') if path.exists() else None
    if not raw:
        raw = safe_request(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
        if raw and '<article' in raw: path.write_text(raw, encoding='utf-8')
    if not raw or '<article' not in raw: return '', 'Open full-text XML unavailable'
    try:
        root = ET.fromstring(raw)
        licenses = ' '.join(' '.join(l.itertext()) + ' ' + ' '.join(str(v) for v in l.attrib.values())
                            for l in root.iter('license')).lower()
        if not any(s in licenses for s in ('creativecommons.org/licenses/', 'creativecommons.org/publicdomain/', 'creative commons', 'cc by', 'cc0')):
            return '', 'License not verified as Creative Commons/public domain'
        body = root.find('.//body')
        if body is None: return '', 'No article body'
        kws = {'1': ['stress','dendrit','depress','adversity'],
               '2': ['social','isolation','loneliness','reject'],
               '3': ['sleep','circadian','wake','spine'],
               '4': ['exercise','environmental enrich','physical','plasticity'],
               '5': ['anhedonia','reward','dopamine','motivat'],
               '6': ['orexin','hypocretin','wake','stress'],
               '7': ['suicid','risk','stress','isolation']}
        words = kws.get(str(section).strip()[:1], ['depress', 'synap', 'stress'])
        candidates = []
        for p in body.iter('p'):
            t = text_from(p)
            if 100 <= len(t) <= 1200:
                score = sum(w in t.lower() for w in words)
                if score >= 2: candidates.append((score, t))
        if candidates:
            return sorted(candidates, key=lambda x: (x[0], -abs(len(x[1])-480)), reverse=True)[0][1], 'CC-licensed full-text paragraph'
        return '', 'No relevant full-text paragraph'
    except (ET.ParseError, ValueError) as e:
        return '', 'XML parse error: ' + str(e)[:80]


def make_word(records):
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(.67)
    doc.styles['Normal'].font.name = 'Calibri'; doc.styles['Normal'].font.size = Pt(9)
    doc.add_heading('Environmental, Behavioral, and Lifestyle Factors', 0)
    doc.add_paragraph('100 selected studies • PubMed / Europe PMC • Source-labelled evidence collection')
    doc.add_paragraph('Verbatim text is included only when the full-text license permits it. Abstracts and original paraphrases are labelled distinctly. Automated selection requires scientific review.')
    count = {'licensed full text': 0, 'abstract': 0, 'input summary': 0, 'none': 0}
    current = None
    for i, rec in enumerate(records, 1):
        pmid = rec['pmid']
        secname = rec['section'] or 'Selected environmental, behavioral and lifestyle factors'
        if secname != current: current = secname; doc.add_heading(secname, level=1)
        print(f'[{i}/{len(records)}] PMID {pmid}', flush=True)
        try:
            m = metadata(pmid)
        except Exception as e:
            print('  metadata problem:', str(e)[:160], flush=True); m = {}
        title = m.get('title') or rec['title'] or f'PubMed article {pmid}'
        authors = m.get('authorString') or rec['authors']
        yr = m.get('pubYear') or rec['year']
        journal = m.get('journalTitle') or rec['journal']
        doi = m.get('doi') or rec['doi']
        doc.add_heading(f'{i:03d}. {title}', 2)
        doc.add_paragraph(f'Authors: {authors or "Not verified"}  |  Year: {yr or "Not verified"}  |  Journal: {journal or "Not verified"}')
        doc.add_paragraph(f'PMID: {pmid}  |  DOI: {doi or "Not available"}  |  PubMed: https://pubmed.ncbi.nlm.nih.gov/{pmid}/')
        pmcid = str(m.get('pmcid', '') or '').strip()
        try:
            passage, detail = licensed_fulltext_paragraph(pmcid, secname)
        except Exception as e:
            passage, detail = '', 'Full text request failed: ' + str(e)[:110]
        kind = 'licensed full text'
        if not passage:
            try: passage = article_abstract(pmid)
            except Exception as e: print('  abstract problem:', str(e)[:120], flush=True)
            kind = 'abstract'
        if not passage:
            passage = rec['summary']; kind = 'input summary'
        if not passage:
            passage = 'No accessible evidence paragraph or input summary. See PubMed record.'; kind = 'none'
        count[kind] += 1
        doc.add_paragraph({'licensed full text': 'EXACT PARAGRAPH FROM OPEN-LICENSED FULL TEXT',
                           'abstract': 'PUBMED ABSTRACT (NOT FULL TEXT)',
                           'input summary': 'ORIGINAL SUMMARY / PARAPHRASE (NOT A QUOTATION)',
                           'none': 'UNAVAILABLE'}[kind], style='Subtitle')
        doc.add_paragraph(passage)
        if pmcid: doc.add_paragraph('Full-text record: https://pmc.ncbi.nlm.nih.gov/articles/' + pmcid + '/')
        if kind != 'licensed full text': doc.add_paragraph('Full-text status: ' + detail)
        if i % 10 == 0:
            doc.save(OUTPUT)
            print('  checkpoint Word saved; counts:', count, flush=True)
        time.sleep(.25)
    doc.add_heading('Extraction summary', level=1)
    for key, val in count.items(): doc.add_paragraph(f'{key}: {val}')
    doc.save(OUTPUT)
    print('\nCOMPLETE:', OUTPUT, '\nSUMMARY:', count, flush=True)
    return OUTPUT


if __name__ == '__main__':
    try:
        result = make_word(input_rows())
        try:
            from google.colab import files
            files.download(result)
        except ImportError:
            pass
    except Exception as e:
        print('\nFATAL SETUP ERROR:', str(e), flush=True)
        print('If GitHub is blocked, upload the previously supplied ZIP into Colab Files and run again.', flush=True)
        sys.exit(1)