# Nutritional Factors and the Gut–Brain Axis — research corpus

**Date:** 2026-11-03. Source data: 7 user-provided PubMed HTML exports.

- **Food 1–6:** 95 + 42 + 21 + 55 + 77 + 289 = 579 original records (537 unique PMIDs).
- **Food 7:** screened 6,812 records; identified 100 selected, grouped by 7 research headings.
- **Total:** 679 list rows, **556 unique PMIDs** after retaining cross-file overlaps; 81 of the chosen 100 also occur in Food 1–6.
- CSV files keep original source membership; the extractor fetches article bibliographic metadata live by PMID from the Europe PMC API.
- The curated 100 are distributed by topic: 13, 15, 14, 14, 18, 12, 14.

## Files

* `articles_for_github.csv`: 679 rows (source group, PMID).
* `selected_100_for_github.csv`: 100 rows (research subsection, PMID).
* `nutrition_colab_extractor.py`: Colab/standard Python extractor using official Europe PMC REST, OA XML and license checks, resume cache, checkpoints, DOCX and status CSV.

## Run in Google Colab

Paste **one line** into a code cell:

```python
!pip -q install python-docx lxml requests && curl -fLsS --retry 5 https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/nutrition_gut_brain_2026/nutrition_colab_extractor.py -o nutrition_colab_extractor.py && python nutrition_colab_extractor.py
```

The complete run processes each unique PMID once, while retaining all source-file affiliations. It creates `/content/Nutrition_GutBrain_Results/Nutritional_FullText_Collected.docx` and a ZIP backup with `retrieval_status.csv`; the ZIP is offered for download at the end.

### Data integrity and permissions

A PubMed abstract is **not** a complete paper. The collector uses Europe PMC metadata and official OA `fullTextXML` only. It places an exact relevant paragraph plus the main JATS article body into Word only for articles whose XML is accessible and carries a compatible Creative Commons reuse license. It marks other articles `abstract_only`, `licence_not_confirmed`, or another status, **never** fabricating article text or bypassing paywalls. Figures, supplementary files, and bibliography lists are not reproduced. All article excerpts should be checked against the published version before quotation.

External sources: Europe PMC REST API and PMC developer reuse policies. No subscription login required. API request volume can make 556-article processing take a substantial period; checkpoints and per-PMID cache allow resuming in the same persistent filesystem. On ephemeral Colab runtimes, copy the output directory to Drive before the session closes if long-term resume is needed.
