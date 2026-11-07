# ONSM article research — 536 records

This directory contains an independent ONSM article-text retrieval project, assembled from eight supplied PubMed HTML lists on 2026-11-07.

- `ONSM_All_536_Records.html`: searchable offline HTML catalog, retaining every source record.
- `records.json`: structured metadata, abstracts, PMID, DOI, original source list and order for 536 records (224 unique PMIDs).
- `onsm_fetch.py`: live OA lookup for distinct articles using Europe PMC, PMC XML, OpenAlex and optionally Unpaywall, with per-PMID checkpoints and fault-tolerant continuation.
- `run_colab.py`: automatic Colab bootstrap; downloads the source files and dependencies, runs retrieval, downloads two Word documents.

## Copy this one line into Google Colab (no file upload)

```python
import urllib.request;exec(urllib.request.urlopen("https://raw.githubusercontent.com/samadzadehartin-svg/test/main/ONSM_Article_Fetch_2026_11_07/run_colab.py").read().decode("utf-8"))
```

Expected Word outputs:
1. `ONSM_All_Articles_FullText_or_Abstract.docx`: all 536 source records; legally accessible full text when retrieved, abstract otherwise.
2. `ONSM_Missing_FullText_DOI_List.docx`: unique titles, author information, DOI and PMID without retrievable full text.

A status CSV is also retained in Colab output. A miss does not establish paywall status. The script does not use Sci-Hub or circumvent paywalls. Retrieval can be incomplete when repositories lack a copy, servers restrict access, or PDFs are scanned.
