#!/usr/bin/env python3
"""Merge data/objects.json + data/curated.json into data/data.js (loaded by index.html).

A .js file (not fetch of .json) is used so the page also works when opened
directly from disk, as well as on GitHub Pages.
Run after harvest.py:  python3 scripts/build_data.py
"""
import json, pathlib, datetime, re


def _bucket(date_text):
    t = str(date_text or "").lower()
    m = re.search(r"(\d{1,2})(st|nd|rd|th)\s*(century|c\b|cent)", t)
    n = int(m.group(1)) if m else None
    if n is None:
        m = re.search(r"\b(\d{3,4})s?\b", t)
        n = int(m.group(1)) // 100 + 1 if m and 100 <= int(m.group(1)) <= 2100 else None
    if n is None:
        return "Undated"
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')} c."

ROOT = pathlib.Path(__file__).resolve().parent.parent
objects = json.load(open(ROOT / "data" / "objects.json"))
si_path = ROOT / "data" / "smithsonian_objects.json"
if si_path.exists():  # produced by scripts/harvest_smithsonian.py
    import re
    si = json.load(open(si_path))
    for o in si:
        o["century"] = _bucket(o["date"])
    objects += si
curated = json.load(open(ROOT / "data" / "curated.json"))
log = json.load(open(ROOT / "data" / "harvest_log.json"))

# Explicit links between harvested records and repatriation entries.
# Only add a link when a source names the exact object.
CLAIM_LINKS = {
    "aic-130700": "Return requested by Nepal in 2021; NHRC lists it as Found Heritage (see Repatriation).",
    "aic-148368": "NHRC identifies this as stolen from Sakhona village, Lazimpat (see Repatriation).",
    "aic-153537": "NHRC identifies this as stolen from I Baha Bahi, Patan (see Repatriation).",
    "aic-151120": "NHRC identifies this as stolen from Khapinchhen Tole, Patan (see Repatriation).",
    "aic-148361": "NHRC identifies this as stolen, from Lalitpur (see Repatriation).",
    "aic-148371": "NHRC lists this accession as stolen under the title Dancing Bhairav (see Repatriation).",
    "lacma-40129": "Matches the 12th-c. copper Buddha with life scenes that activists have asked LACMA to return (see Repatriation).",
}

bm_path = ROOT / "data" / "bm_objects.json"
if bm_path.exists():  # produced by scripts/import_bm.py (British Museum, CC BY-NC-SA 4.0, used with permission)
    bm = json.load(open(bm_path))
    for o in bm:
        o["century"] = _bucket(o["date"])
    objects += bm

lacma_path = ROOT / "data" / "lacma_objects.json"
if lacma_path.exists():  # produced by scripts/harvest_lacma.py
    lac = json.load(open(lacma_path))
    for o in lac:
        o["century"] = _bucket(o["date"])
    objects += lac

jc_path = ROOT / "data" / "joconde_objects.json"
if jc_path.exists():  # produced by scripts/import_joconde.py (Licence Ouverte 2.0, Ministère de la Culture)
    jc = json.load(open(jc_path))
    for o in jc:
        o["century"] = _bucket(o["date"])
    objects += jc

man_path = ROOT / "data" / "manual_objects.json"
if man_path.exists():  # hand-entered records from institutions without open data (facts only, sourced per record)
    man = json.load(open(man_path))
    for o in man:
        o["century"] = _bucket(o["date"])
    objects += man

thumbs_path = ROOT / "data" / "thumbs.json"
thumbs = set(json.load(open(thumbs_path))) if thumbs_path.exists() else set()
for o in objects:
    if o["id"] in thumbs:
        o["thumb"] = f"images/thumbs/{o['id']}.jpg"

for o in objects:
    if o["id"] in CLAIM_LINKS:
        o["claim"] = CLAIM_LINKS[o["id"]]

payload = {
    "built": datetime.date.today().isoformat(),
    "harvested": log.get("harvested"),
    "metMissing": log.get("met_ids_returned_404", []),
    "objects": objects,
    **curated,
}
out = ROOT / "data" / "data.js"
out.write_text("window.NEPAL_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

# Also write a flat CSV for people who want the data without the site.
import csv
cols = ["id", "source", "country", "title", "date", "century", "type", "medium", "place", "accession",
        "credit", "provenance", "openImage", "image", "url", "dataLicence", "matchBasis", "strength"]
with open(ROOT / "data" / "objects.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(objects)
print(f"wrote {out} ({out.stat().st_size/1e6:.2f} MB), {len(objects)} objects")
