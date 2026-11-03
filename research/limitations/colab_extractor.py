#!/usr/bin/env python3
"""Google Colab entry point for the 859-PMID limitations evidence extraction.

The implementation is stored in extractor_source.b64 (gzip+base64).
A readable, uncompressed version is also available as a file in ChatGPT.
The implementation queries PubMed for bibliographic metadata and only reads
openly available full-text XML from Europe PMC / NCBI BioC.
"""
import base64
import gzip
import urllib.request

URL = "https://raw.githubusercontent.com/samadzadehartin-svg/test/main/research/limitations/extractor_source.b64"
with urllib.request.urlopen(URL, timeout=30) as response:
    compressed_source = response.read().strip()
source = gzip.decompress(base64.b64decode(compressed_source))
exec(compile(source.decode("utf-8"), "open_access_extractor.py", "exec"), {"__name__":"__main__"})
