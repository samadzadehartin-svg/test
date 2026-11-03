# Limitations and Future Research Directions — Selected PubMed Literature

Curated from **nine user-provided PubMed HTML exports** on 2026-11-03.

## Selection rule and counts

| Original file | Input records | Selected rows | Rule |
|---|---:|---:|---|
| Limitations 1 | 6812 | 400 | Highest-ranked 400 |
| Limitations 2 | 93 | 93 | All |
| Limitations 3 | 71 | 71 | All |
| Limitations 4 | 9 | 9 | All |
| Limitations 5 | 666 | 400 | Highest-ranked 400 |
| Limitations 6 | 996 | 400 | Highest-ranked 400 |
| Limitations 7 | 213 | 213 | All |
| Limitations 8 | 101 | 101 | All |
| Limitations 9 | 198 | 198 | All |

**Total input: 9159 records. Selected within files: 1885 records. After PMID-based deduplication: 1211 articles; 674 cross-file redundant selections.**

All records in source files with fewer than 500 records were included by rule, even if not every record is clinically or morphologically central. Ranking is a reproducible title/abstract heuristic, **not an expert appraisal of every full text**. The document `Core_References_6_Subsections.docx` provides a focused shortlist of 28 distinct references.

## Files

- `ranked_articles_manifest.csv`: 1211 unique PMIDs with full citation metadata, relevant source-abstract evidence, rank, topic and source-file provenance. This is the input used by the Colab script.
- `ranked_articles.csv`: larger record table including fully formatted citation and source-abstract excerpt.
- `per_file_selected_1885.csv`: transparent record-level selections before cross-file deduplication.
- `colab_extractor.py`: downloads the manifest and retrieves Europe PMC **open-access** complete article text; a fallback to abstracts is clearly labeled.

## Google Colab (one cell)

```python
!wget -q https://raw.githubusercontent.com/samadzadehartin-svg/test/main/limitations_2026/colab_extractor.py -O limitations_colab.py && python limitations_colab.py
```

Output directory: `/content/limitations_oa_results`.

- `Evidence_Paragraphs_ALL.docx`: full metadata and one source paragraph per record. `FULL_TEXT` or `ABSTRACT` evidence explicitly indicated.
- `FullTexts_OpenAccess_ALL.docx`: full body text of all open-access works successfully retrieved through Europe PMC.
- `Availability_Report.csv`: per-PMID provenance and availability/failure status.
- `Results_Word_and_CSV.zip`: packaged Word and CSV deliverables.

The script saves a JSONL cache after each article and can resume after interrupted runs. The combined full-text document may be very large and the program saves periodic document checkpoints.

## Scientific caveats

1. **A PMID may identify a preprint version of a subsequently published paper.** For example PMID 36778310 is a preprint associated with the published PMID 39191313. They must not be treated as two independent original studies.
2. SV2A PET is a proxy for synaptic density, **not a direct technique for counting or measuring dendritic spines in living humans**.
3. Postmortem observational results do not by themselves establish that dendritic spine changes caused depression or suicidal behavior.
4. Publicly available bibliographic information and abstracts do not imply permission to bulk-download the publisher's paywalled complete text. We use authorized Europe PMC open-access XML for full text. The user is responsible for terms of each article's license.
5. The open-access retrieval has to run in a network-enabled environment (such as Google Colab). It has not been executed in the local sandbox.