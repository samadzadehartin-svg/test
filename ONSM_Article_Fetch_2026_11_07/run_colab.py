#!/usr/bin/env python3
"""One-click Google Colab runner for the ONSM article collection."""
import os
import sys
import time
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://raw.githubusercontent.com/samadzadehartin-svg/test/main/ONSM_Article_Fetch_2026_11_07/"
WORK = Path("/content/ONSM_Article_Fetch_2026_11_07")
WORK.mkdir(parents=True, exist_ok=True)
OUT = Path("/content/ONSM_Results")

def fetch(filename):
    destination = WORK / filename
    last_error = None
    for attempt in range(1, 5):
        try:
            req = Request(BASE + filename, headers={"User-Agent": "Mozilla/5.0 ONSM-Research-Colab"})
            with urlopen(req, timeout=90) as response:
                blob = response.read()
            if len(blob) < 100:
                raise ValueError("Unexpectedly small file: " + filename)
            destination.write_bytes(blob)
            print("[DOWNLOAD]", filename, len(blob), "bytes", flush=True)
            return
        except Exception as err:
            last_error = err
            print("[RETRY]", filename, attempt, str(err), flush=True)
            time.sleep(min(attempt * 2, 8))
    raise RuntimeError(f"Failed to download {filename}: {last_error}")

for filename in ("records.json", "onsm_fetch.py"):
    fetch(filename)

print("Installing dependencies (requests, beautifulsoup4, lxml, python-docx, pymupdf, trafilatura)...", flush=True)
subprocess.run([sys.executable, "-m", "pip", "-q", "install",
                "requests", "beautifulsoup4", "lxml", "python-docx", "pymupdf", "trafilatura"],
               check=True)
cmd = [sys.executable, str(WORK / "onsm_fetch.py"),
       "--input", str(WORK / "records.json"), "--output", str(OUT)]
email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
if email:
    cmd.extend(["--email", email])
print("Starting live retrieval for unique PMIDs; duplicates will appear in the Word output.", flush=True)
subprocess.run(cmd, check=True)

from google.colab import files
for filename in ("ONSM_All_Articles_FullText_or_Abstract.docx", "ONSM_Missing_FullText_DOI_List.docx"):
    target = OUT / filename
    if not target.is_file():
        raise FileNotFoundError("Expected Word output missing: " + str(target))
    print("Downloading", target.name, flush=True)
    files.download(str(target))
print("Completed. The two Word documents are downloaded; audit CSV is saved in", OUT, flush=True)
