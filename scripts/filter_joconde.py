#!/usr/bin/env python3
"""
Extract Nepal-related records from Joconde, the national catalogue of the Musées de France
(includes the Musée Guimet and other French museums).

Source: data.gouv.fr dataset "Collections des musées de France : base Joconde"
        (Ministère de la Culture), Licence Ouverte / Open Licence 2.0, CSV about 1.1 GB, updated weekly.
The file is STREAMED and filtered on the fly — the full 1.1 GB is never saved to disk.

Run (Python 3.8+, no extra packages):
    python3 filter_joconde.py
Output: joconde_nepal.csv (same columns as Joconde, only matching rows)

If you already downloaded the CSV, pass its path instead:
    python3 filter_joconde.py path/to/joconde.csv
"""
import csv, io, re, sys, time, urllib.request

URL = "https://www.data.gouv.fr/api/1/datasets/r/7e3307c2-f2ff-455c-bbca-bb6f11aec7bb"
OUT = "joconde_nepal.csv"
# Matched against the whole record (every column). Broad on purpose; the importer
# decides later which matches are genuinely Nepalese.
TERMS = re.compile(r"n[ée]pal|katmandou|kathmandu|katmandu|bhaktapur|bhadgaon|lalitpur|patan|n[ée]war|licchavi|gurkha|gorkha|sherpa", re.I)
csv.field_size_limit(sys.maxsize if sys.maxsize < 2**31 else 2**31 - 1)


def open_source():
    if len(sys.argv) > 1:
        return open(sys.argv[1], "rb")
    req = urllib.request.Request(URL, headers={"User-Agent": "nepal-heritage-abroad/1.0 (non-commercial research catalogue)"})
    return urllib.request.urlopen(req, timeout=120)


raw = open_source()
text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
first = text.readline()
delim = ";" if first.count(";") > first.count(",") else ","
header = next(csv.reader([first], delimiter=delim))
print(f"Columns ({len(header)}), delimiter '{delim}':")
print("  " + " | ".join(header))

reader = csv.reader(text, delimiter=delim)
kept = scanned = 0
start = time.time()
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    for row in reader:
        scanned += 1
        if TERMS.search(" ".join(row)):
            w.writerow(row)
            kept += 1
        if scanned % 100000 == 0:
            print(f"  {scanned:,} records scanned, {kept:,} kept ({time.time() - start:.0f}s)")

print(f"Done: {scanned:,} scanned, {kept:,} kept -> {OUT}")
print("Upload joconde_nepal.csv to the chat.")
