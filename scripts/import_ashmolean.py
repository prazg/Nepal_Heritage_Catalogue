#!/usr/bin/env python3
"""
Import an Ashmolean Museum (Oxford) Collections Online CSV export.

The export (21 Sep 2026) separates records with the literal text "undefined" instead of line
breaks; this is repaired before parsing. Object links use the address the museum's own
collections.ashmolean.org/object/<id> redirects to.

Run:  python3 scripts/import_ashmolean.py data/raw/ashmolean_export_2026-09-21.csv
Output: data/ashmolean_objects.json
"""
import csv, io, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEPAL = re.compile(r"nepal|kathmandu|bhaktapur|lalitpur|patan|newar|licchavi|malla", re.I)

raw = open(sys.argv[1], encoding="utf-8-sig").read()
rows = list(csv.DictReader(io.StringIO(raw.replace('"undefined"', '"\n"'))))


def clean_date(s):
    parts = [re.sub(r"\s*-\s*date of creation$", "", p.strip()) for p in s.split(",") if p.strip()]
    return "; ".join(parts)


def leaf(s):
    return ", ".join(dict.fromkeys(x.split(">")[-1].strip() for x in s.split(",") if x.strip()))


out = []
for r in rows:
    place = "; ".join(p.replace("Asia > ", "").replace(" > ", ", ") for p in r["Place"].split(", Asia > ") if p)
    strong = bool(NEPAL.search(r["Place"]) or NEPAL.search(r["Date / Period"]))
    out.append({
        "source": "Ashmolean Museum, Oxford", "country": "UK", "id": "ash-" + r["recordId"],
        "title": r["Title"], "date": clean_date(r["Date / Period"]), "type": leaf(r["type of object"]),
        "medium": r["Material /Technique"].split(",")[0].strip(), "place": place,
        "accession": r["Accession number"], "credit": r["Person / organisation - Role"],
        "provenance": "", "description": "", "image": "", "openImage": False,
        "url": f"https://www.ashmolean.org/collections-online#/item/ash-object-{r['recordId']}",
        "dataLicence": "Ashmolean Collections Online export (images not reproduced)",
        "matchBasis": ("Place of creation: " + place) if strong else ("Place given only as: " + place + " — check"),
        "strength": "strong" if strong else "weak",
    })

json.dump(out, open(ROOT / "data" / "ashmolean_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(out), "records;", Counter(o["strength"] for o in out))
