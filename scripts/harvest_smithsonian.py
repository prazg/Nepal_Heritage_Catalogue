#!/usr/bin/env python3
"""
Harvest Nepal-related records from the Smithsonian Open Access dataset on AWS.

Source: https://registry.opendata.aws/smithsonian-open-access/  (CC0, updated weekly)
Public S3 bucket, read over HTTPS; no AWS account or API key needed.
Layout checked 16 Sep 2026: metadata/edan/<unit>/00.txt … ff.txt, one JSON record per line.

Streams each file and keeps only lines mentioning Nepal-related terms, so the
multi-GB dataset is never stored. Output: data/raw/smithsonian.json

Run:  python3 scripts/harvest_smithsonian.py            (default units)
      python3 scripts/harvest_smithsonian.py nmah sil   (choose units)
"""
import json, re, sys, pathlib, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
BUCKET = "https://smithsonian-open-access.s3-us-west-2.amazonaws.com"
# National Museum of Asian Art objects (fsg, nmaa) and archives (fsa); anthropology archives,
# films and collections (naa, hsfa, nmnhanthro); Folklife; Cooper Hewitt.
DEFAULT_UNITS = ["fsg", "nmaa", "fsa", "naa", "hsfa", "nmnhanthro", "cfchfolklife", "chndm"]
UNITS = sys.argv[1:] or DEFAULT_UNITS
TERMS = re.compile(rb"nepal|kathmandu|katmandu|bhaktapur|lalitpur|patan, |newar|gurkha|gorkha|sherpa|nipal", re.I)
FILES = [f"{i:02x}.txt" for i in range(256)]


def scan(unit_file):
    unit, fname = unit_file
    hits = []
    try:
        with urllib.request.urlopen(f"{BUCKET}/metadata/edan/{unit}/{fname}", timeout=120) as r:
            for line in r:
                if TERMS.search(line):
                    hits.append(json.loads(line))
    except Exception as e:
        print(f"  ! {unit}/{fname}: {e}", file=sys.stderr)
    return hits


jobs = [(u, f) for u in UNITS for f in FILES]
found = []
with ThreadPoolExecutor(16) as ex:
    for i, hits in enumerate(ex.map(scan, jobs), 1):
        found += hits
        if i % 256 == 0:
            print(f"  {UNITS[i // 256 - 1]} done, {len(found)} candidate records so far")

json.dump(found, open(RAW / "smithsonian.json", "w"), ensure_ascii=False)
print("candidates:", len(found))

# ---------------------------------------------------------------- normalise
# strong  = Nepal term in a place / culture / geoLocation field or the title
# mention = Nepal term only elsewhere (notes, citations, exhibition history); shown as weak
import re as _re
CORE = _re.compile(r"\b(nepal\w*|kathmandu|katmandu|bhaktapur|lalitpur|newar|newari|nipal)\b", _re.I)
UNIT_NAMES = {"NAA": "Smithsonian — National Anthropological Archives", "HSFA": "Smithsonian — Human Studies Film Archives",
              "FSA": "Smithsonian — National Museum of Asian Art Archives", "CFCHFOLKLIFE": "Smithsonian — Ralph Rinzler Folklife Archives"}


def first(ft, key, label=None):
    for it in ft.get(key, []) or []:
        if label is None or it.get("label") == label:
            return str(it.get("content", ""))
    return ""


out, seen = [], set()
for r in found:
    ct = r.get("content", {})
    dn = ct.get("descriptiveNonRepeating", {}) or {}
    is_archive = not dn  # EAD archival records keep fields at content level
    key = dn.get("record_ID") or ct.get("record_id") or r.get("id")
    if key in seen:
        continue
    seen.add(key)
    ist, ft = ct.get("indexedStructured", {}) or {}, ct.get("freetext", {}) or {}
    placeish = json.dumps([ist.get("place"), ist.get("geoLocation"), ist.get("culture"), ft.get("place"), ft.get("culture"),
                           [i for i in ft.get("odd", []) or [] if i.get("label") == "Place"]])
    title = r.get("title") or (dn.get("title") or {}).get("content", "") or "Untitled"
    if CORE.search(placeish) or CORE.search(title):
        strength = "strong"
    elif CORE.search(json.dumps(ct)):
        strength = "weak"
    else:
        continue  # line matched only a broad term (e.g. Newark, Sherpa elsewhere); drop
    src = dn.get("data_source") or first(ft, "dataSource") or UNIT_NAMES.get((r.get("unitCode") or "").upper(), "Smithsonian — " + (r.get("unitCode") or ""))
    src = {"Ralph Rinzler Folklife Archives and Collections": "Ralph Rinzler Folklife Archives",
           "NMNH - Anthropology Dept.": "Natural History, Anthropology"}.get(src, src)
    if not src.startswith("Smithsonian"):
        src = "Smithsonian — " + src
    media = ((dn.get("online_media") or {}).get("media") or [{}])[0]
    cc0 = (media.get("usage") or {}).get("access") == "CC0"
    places = [str(i.get("content", "")) for i in ft.get("place", []) or []]
    prov = " ".join(str(i.get("content", "")) for i in ft.get("notes", []) or [] if i.get("label") == "Provenance")
    link = dn.get("record_link") or ct.get("record_link") or dn.get("guid") or ct.get("guid") or ""
    obj_date = first(ft, "date", "Date") or first(ft, "date", "Collection Date") or first(ft, "unitdate") or ""
    sets = [str(i.get("content", "")) for i in ft.get("setName", []) or []]
    collection = max(sets, key=len) if sets else ""
    people = "; ".join(f"{i.get('label')}: {i.get('content')}" for i in ft.get("name", []) or []
                       if i.get("label") in ("Donor Name", "Collector", "Collection Creator", "Creator", "Photographer"))
    out.append({
        "source": src, "country": "USA", "id": "si-" + str(key),
        "title": title, "date": obj_date,
        "type": ((ist.get("object_type") or [""])[0]) or first(ft, "objectType"),
        "medium": first(ft, "physicalDescription"), "place": "; ".join(places) or first(ft, "culture"),
        "accession": first(ft, "identifier") or first(ft, "container"),
        "credit": "; ".join(x for x in [first(ft, "creditLine"), people, ("Part of: " + collection) if collection and collection != "Anthropology" else ""] if x),
        "provenance": re.sub(r"\s+", " ", prov)[:900],
        "image": (media.get("thumbnail") or "") if cc0 and media.get("type") == "Images" else "",
        "openImage": cc0 and media.get("type") == "Images",
        "url": link, "dataLicence": "CC0 (Smithsonian Open Access)",
        "matchBasis": "Nepal in place/culture/title" if strength == "strong" else "Nepal mentioned only in notes or citations — check",
        "strength": strength})

json.dump(out, open(ROOT / "data" / "smithsonian_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter((o["source"], o["strength"]) for o in out))
