# Dendritic Spine Alterations in Depression and Suicidal Behavior — Limitations

This folder supports the review subsection **Limitations and Future Research Directions**, covering six themes: human/animal study limitations, challenges imaging living human dendritic spines, regional/cellular/individual heterogeneity, medication and comorbidity confounders, causal inference, and experimental/clinical priorities.

**Input:** 9 user-supplied PubMed HTML exports, containing 9,159 entries. Rule applied independently to each input: under 500 entries, keep all; 500 or more, keep the highest ranked 400. This gives **1,885 selected slots**, and **1,252 distinct PubMed IDs** after deduplication (633 repeated slots). Selection is algorithmic screening, not peer review. A more carefully curated shortlist of 37 recommended papers and a full 1,252-record bibliographic index are provided separately in the ChatGPT response.

## Colab: one line (complete run)

```python
!pip -q install requests lxml python-docx tqdm && wget -q https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research-dendritic-spine-limitations/colab_run.py -O colab_run.py && python colab_run.py
```

For a short test add `--limit 3`; for a persistent Google Drive output location add `--output /content/drive/MyDrive/limitations_fulltext` after mounting Drive. By default the script processes all 1,252 IDs, retrieves citation metadata from Europe PMC, downloads JATS full-text XML **only when an OA marker is present and the endpoint provides it**, and labels everything else as `ABSTRACT_ONLY`. It builds `Limitations_OA_FullText.docx` (complete available OA article body text, or clearly labeled abstract for other articles), `Limitations_Exact_Evidence_Paragraphs.docx` (one sourced paragraph/abstract per item) and `retrieval_status.csv`. The local cache saves responses to allow resuming within a retained working directory. This doesn't bypass university logins or paywalls.

## Files

- `selected_pmids_delta.b64` is a compact, verifiable list of exactly 1,252 unique PMIDs, delta-coded, zlib-compressed and base64-encoded (in numeric ascending order).
- `colab_run.py` is the self-contained collector and Word exporter.
- `index.html` is a browser-friendly dynamic PubMed catalog (requires access to Europe PMC in the browser for title metadata).

**Licensing:** Check the specific article's license before reuse or redistributing extracted full text. This repository contains no copyrighted publisher full texts. Data sources: Europe PMC REST API and PubMed / PMC. Not all free-to-read content is open for machine reuse.