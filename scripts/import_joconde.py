#!/usr/bin/env python3
"""
Import Joconde records (national catalogue of the Musées de France, Ministère de la Culture).
Licence Ouverte / Open Licence 2.0 — attribution: "Ministère de la Culture, base Joconde".

Accepts:
  - an export from pop.culture.gouv.fr (.xlsx: criteria row, French labels row, field-code row, then data)
  - joconde_nepal.csv from scripts/filter_joconde.py (field codes as header)
Several files can be given; records are de-duplicated by Joconde reference (REF).
Output: data/joconde_objects.json
Run:  python3 scripts/import_joconde.py data/raw/*.xlsx data/raw/joconde_nepal.csv
"""
import json, pathlib, re, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEPAL = re.compile(r"n[ée]pal|katmandou|kathmandu|bhaktapur|bhadgaon|lalitpur|patan \(n|n[ée]war|licchavi", re.I)
PLACE_FIELDS = ["ECOL", "LIEUX", "PLIEUX", "GEOHI", "DECV", "PDEC"]
# Joconde spells the same museum several ways; normalise so each museum appears once
MUSEUM_ALIASES = {"musée des arts asiatiques guimet": "Musée Guimet"}


def load(path):
    p = pathlib.Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        raw = pd.read_excel(p, header=None, dtype=str)
        code_row = next(i for i in range(min(10, len(raw))) if "REF" in raw.iloc[i].tolist())
        df = raw.iloc[code_row + 1:].copy()
        df.columns = raw.iloc[code_row].tolist()
    else:
        df = pd.read_csv(p, dtype=str)
    return df.fillna("")


def g(r, k):
    v = r.get(k, "")
    return str(v).strip() if isinstance(v, str) else ""


out = {}
for path in sys.argv[1:]:
    for _, r in load(path).iterrows():
        ref = g(r, "REF")
        if not ref or ref in out:
            continue
        if not NEPAL.search(" ".join(str(v) for v in r.values)):
            continue  # e.g. a whole-museum export: keep only records that mention Nepal somewhere
        museum = g(r, "NOMOFF") or g(r, "LOCA").split(";")[-1].strip()
        city = g(r, "VILLE_M")
        placeish = " ".join(g(r, k) for k in PLACE_FIELDS)
        strong = bool(NEPAL.search(placeish))
        ecol = g(r, "ECOL")
        foreign_school = bool(ecol) and not NEPAL.search(ecol)
        prov = "; ".join(x for x in [
            ("Acquired " + g(r, "DACQ")) if g(r, "DACQ") else "",
            g(r, "STAT"),
            ("Former owners: " + g(r, "APTN")) if g(r, "APTN") else "",
            g(r, "HIST")] if x)
        museum = MUSEUM_ALIASES.get(museum.lower(), museum[:1].upper() + museum[1:])
        out[ref] = {
            "source": museum if museum == "Musée Guimet" else f"{museum}, {city}" if city and city not in museum else (museum or "French museum (Joconde)"),
            "country": "France", "id": "jc-" + ref,
            "title": g(r, "TITR") or g(r, "APPL") or g(r, "DENO").capitalize() or "Untitled",
            "date": g(r, "PERI") or g(r, "MILL") or g(r, "EPOQ"),
            "type": g(r, "DENO") or g(r, "DOMN"),
            "medium": g(r, "TECH"),
            "place": "; ".join(x for x in [g(r, "ECOL"), g(r, "LIEUX"), g(r, "PLIEUX")] if x),
            "accession": g(r, "INV"),
            "credit": g(r, "REPR"),
            "provenance": prov[:900],
            "description": g(r, "DESC")[:400],
            "image": "", "openImage": False,
            "url": f"https://pop.culture.gouv.fr/notice/joconde/{ref}",
            "dataLicence": "Licence Ouverte 2.0 — Ministère de la Culture, base Joconde",
            "matchBasis": ("Made in Nepal, but the school/artist is recorded as " + ecol + " — check" if strong and foreign_school
                           else "Nepal in school, place of creation/use or collection fields" if strong
                           else "Nepal mentioned elsewhere in the record — check"),
            "strength": "strong" if strong and not foreign_school else "weak",
            "joconde_museum": museum,
        }

pop_img = ROOT / "data" / "raw" / "joconde_pop_images.json"
imgs = json.load(open(pop_img)) if pop_img.exists() else {}
for ref, o in out.items():
    v = imgs.get(ref, {})
    o["imageKey"] = "joconde"
    ok = v.get("IMG") and (v.get("DIFFU") or "").lower() != "non"
    o["imageCandidate"] = "https://popcorn-prd-perf-assets.s3.gra.io.cloud.ovh.net/" + v["IMG"][0] if ok else ""
    o["imageCreditText"] = ((v.get("COPY") or "© " + o["source"]) + " — via POP, Ministère de la Culture; shown with permission.") if ok else ""
json.dump(list(out.values()), open(ROOT / "data" / "joconde_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(out), "records;", Counter(o["strength"] for o in out.values()), "; by museum:", Counter(o["joconde_museum"] for o in out.values()))
