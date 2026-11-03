# Dendritic spine — Limitations & Future Research Directions

This folder contains a reproducible research-evidence pipeline for 859 unique PubMed identifiers selected from nine PubMed HTML exports.

## Files
- `selected_pmids_compact.txt` — 859 unique PMIDs in ranked order, priority A/B/C, best matching topic index (0–5).
- `colab_extractor.py` — Colab-friendly launcher.
- `extractor_source.b64` — complete extractor implementation encoded as gzip + base64, to avoid copying a large script into Colab.

## One-line Google Colab cell (Python)
```python
import sys,subprocess,urllib.request; subprocess.check_call([sys.executable,'-m','pip','-q','install','python-docx','requests','lxml']); exec(urllib.request.urlopen('https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/limitations/colab_extractor.py').read().decode('utf-8'))
```

## Output
A DOCX with the full citation, subsection, an exact complete article paragraph from accessible full-text XML when obtainable, or a clearly labelled PubMed abstract passage otherwise. A CSV status report documents which records could be retrieved. Cache is saved under `/content/limitations_evidence` for resume during the same Colab session.

The extractor checks NCBI PubMed metadata and authorized open full-text sources (Europe PMC, NCBI BioC). It **does not bypass publisher paywalls**, and it does **not fabricate missing text**. It extracts the single highest-scoring relevant full-text paragraph per article; it is an evidence compilation, not an archive of entire manuscripts. For permission to reproduce copyrighted material, follow each publisher's license and terms.

## Six topics (topic index)
0. Limitations of Human and Animal Studies
1. Challenges in Assessing Dendritic Spines in the Living Human Brain
2. Regional, Cellular, and Individual Heterogeneity
3. Medication Effects, Comorbidities, and Other Potential Confounders
4. Distinguishing Correlation from Causation
5. Priorities for Future Experimental and Clinical Research
