# Integrative Mechanisms and Clinical Perspectives

**Source:** Twelve PubMed HTML export files supplied by the researcher.
**Coverage:** 12,087 input records; 1,821 selected record slots; 1,112 unique articles after removing 709 duplicate slots.

Selection: under 300 per HTML => all; over 300 => top 200, with section-diversified relevance screening.

This folder provides the article manifest and a Google Colab script. The script retrieves only machine-readable Open Access full text available through Europe PMC / NCBI BioC APIs. It produces a Word of one relevant exact passage per article (otherwise marked *abstract only*) and a second Word with the full textual bodies of OA articles. It never fabricates inaccessible passages. PDFs, figures, tables, and publisher-paywalled full texts are not included.

## Run
```python
!pip -q install requests python-docx && python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/samadzadehartin-svg/test/main/integrative-research-2026/colab_fulltext_extractor.py','extractor.py')" && python extractor.py
```

When an extraction is interrupted, restart the same command with your output directory preserved, so the caching mechanism can resume from saved records. Full metadata and exact abstracts from the uploaded records are separately available in the original downloadable research package.

**License note:** Availability of PMC XML is not the same as unrestricted redistribution. Check the license of each article before republishing any extracted body text.