# ONSM corpus extraction — 2026-11-07

This GitHub folder includes an exact-order compact PMID manifest for **536 selected records / 224 unique PMIDs**, sourced from eight user-provided PubMed HTML exports, and a Python launcher for Google Colab.

- `ONSM_All_536_Records.html`: compact GitHub manifest with all ordered identifiers (not the complete offline abstracts HTML).
- `onsm_fulltext_colab.py`: self-extracting, resumable Python implementation. To unpack and inspect the full source: `python onsm_fulltext_colab.py --extract`.

## Colab

Paste this **single line** in a Colab code cell:

```python
import subprocess; from google.colab import files; subprocess.run("pip -q install requests beautifulsoup4 lxml pymupdf python-docx && wget -q -O ONSM_All_536_Records.html https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/onsm-2026-11-07/ONSM_All_536_Records.html && wget -q -O onsm_fulltext_colab.py https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/onsm-2026-11-07/onsm_fulltext_colab.py && python onsm_fulltext_colab.py --html ONSM_All_536_Records.html --out ONSM_Results --workers 3", shell=True, check=True); files.download("ONSM_Results_Word_Reports.zip")
```

Outputs: `01_ONSM_FullText_and_Abstracts.docx`, `02_ONSM_No_FullText_DOI_List.docx`, a 536-row audit CSV, a summary JSON and resumable `article_cache/` checkpoints.

Source order and repeated PMIDs are retained in the report's provenance mapping. Full text is retrieved once per unique PMID; duplicate rows are not redundantly downloaded. The online compact manifest uses the Europe PMC API to restore bibliography metadata at runtime. For offline, exact original bibliographic fields and abstracts, use the full HTML delivered with the downloadable project ZIP.

**Sources:** Europe PMC OA full-text XML, OpenAlex OA locations, optional Unpaywall (provide `UNPAYWALL_EMAIL`), user-authorized local PDFs in `authorized_pdfs/`. Failure falls back to an existing or Europe PMC abstract. This code does **not** use Sci-Hub or evade access restrictions.

**Important:** Access is not guaranteed. API rate limits, unavailable full text, and scanned/unextractable PDFs may prevent a match. Re-running resumes cached results; use `--refresh` to retry unsuccessful cached lookups. Full journal PDF figures/tables are not embedded as images in Word; extracted text is included when accessible.
