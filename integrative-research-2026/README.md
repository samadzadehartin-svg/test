# Integrative Mechanisms and Clinical Perspectives — PubMed full-text collector

**Source:** 12 PubMed HTML files supplied by the researcher. 12,087 records scanned; per-file rule applied (all when <300, top 200 when >300): 1,821 selected slots, then 709 repeat slots removed = **1,112 unique PMID articles**.

## Reproducible article list on GitHub
Six numbered `parts/selected_ids_01.txt` to `selected_ids_06.txt` files make up the *complete* 1,112-article, ranked, de-duplicated list. Each entry contains `PMID:review_section_number`; the script verifies all 1,112 IDs before starting.

## ONE-LINE Google Colab command
Paste this entire line into a code cell, then run:

```python
!pip -q install requests python-docx && python -c "import urllib.request as u; b='https://raw.githubusercontent.com/samadzadehartin-svg/test/main/integrative-research-2026/'; [u.urlretrieve(b+n,n) for n in ('colab_fulltext_extractor.py','retrieval_utils.py','make_docx.py')]" && python colab_fulltext_extractor.py
```

Colab downloads the three Python files from GitHub automatically; they retrieve the six GitHub manifest parts. No manual article list upload is required. Every 25 articles, progress is printed. Network/API errors are retried and individual failures do not halt the job. Cached results are saved under `/content/IntegrativeResearch/cache` (a fresh Colab runtime is temporary; copy the folder to Google Drive for persistence).

## What the Colab job generates
- `Integrative_Evidence_Paragraphs.docx`: reference information + exact selected body paragraph when accessible; otherwise exact abstract clearly labeled `ABSTRACT_ONLY`.
- `Integrative_OA_Full_Texts.docx`: all retrieved textual body paragraphs for each article accessible through official OA text APIs; other articles are not represented as full text.
- `Retrieval_Status.csv`: article-specific source/result audit.
- `Integrative_Word_Outputs.zip`: above outputs, automatically offered for download.

Only official Europe PMC REST/JATS XML and NCBI BioC PMC Open Access are used for automated full-text retrieval, not publisher HTML scraping. Articles with paywalled, PDF-only, inaccessible or unlicensed full texts cannot be guaranteed. Tables, images and figures are not represented in Word full-text output. Check the particular article license before further redistribution.

The separate **initial** Word and CSV/JSON research package made from the user-provided HTML contains article citations and verbatim abstracts; it is not falsely labeled full text.

## Files
- `colab_fulltext_extractor.py` — workflow coordinator, GitHub manifest loader, cache, concurrency.
- `retrieval_utils.py` — metadata/official OA API retrieval and exact paragraph choice.
- `make_docx.py` — full-text and evidence Word output + ZIP.
- `parts/` — 1,112 selected unique PubMed IDs in six files.
