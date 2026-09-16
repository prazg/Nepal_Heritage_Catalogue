#!/usr/bin/env python3
"""
Harvest Nepal-related records from open museum collection APIs.

Every endpoint and field used here was tested live on 16 Sep 2026.
APIs change; if a harvester fails, check the institution's current API docs.

Output: data/raw/<source>.json and data/objects.json (normalised).
Run:    python3 scripts/harvest.py
"""
import json, time, re, sys, pathlib, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "nepal-heritage-abroad-catalogue/1.0 (research; non-commercial)",
      "AIC-User-Agent": "nepal-heritage-abroad-catalogue/1.0"}


def get(url, data=None, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **({"Content-Type": "application/json"} if data else {})})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                print(f"  ! failed {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))


def clean(s, n=600):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def century_bucket(date_text):
    """Very rough bucketing for the filter UI. Returns e.g. '12th c.' or 'Undated'."""
    if not date_text:
        return "Undated"
    t = str(date_text).lower()
    m = re.search(r"(\d{1,2})(st|nd|rd|th)\s*(century|c\b|cent)", t)
    if m:
        return ordinal(int(m.group(1))) + " c."
    m = re.search(r"\b(\d{3,4})s?\b", t)
    if m:
        y = int(m.group(1))
        if 100 <= y <= 2100:
            return ordinal(y // 100 + 1) + " c."
    return "Undated"


objects = []

# ---------------------------------------------------------------- Art Institute of Chicago (CC0 data)
print("AIC …")
body = json.dumps({"query": {"bool": {"should": [{"match_phrase": {"place_of_origin": t}} for t in
                    ["Nepal", "Kathmandu", "Patan", "Bhaktapur", "Lalitpur"]]}}, "limit": 100,
                   "fields": ["id", "title", "date_display", "medium_display", "place_of_origin",
                              "artwork_type_title", "credit_line", "main_reference_number",
                              "provenance_text", "image_id", "is_public_domain", "thumbnail"]}).encode()
aic = get("https://api.artic.edu/api/v1/artworks/search", data=body)
json.dump(aic, open(RAW / "aic.json", "w"), indent=1)
for a in (aic or {}).get("data", []):
    objects.append({
        "source": "Art Institute of Chicago", "country": "USA", "id": f"aic-{a['id']}",
        "title": a["title"], "date": a.get("date_display") or "", "type": a.get("artwork_type_title") or "",
        "medium": a.get("medium_display") or "", "place": a.get("place_of_origin") or "",
        "accession": a.get("main_reference_number") or "", "credit": a.get("credit_line") or "",
        "provenance": clean(a.get("provenance_text"), 900),
        "image": f"https://www.artic.edu/iiif/2/{a['image_id']}/full/843,/0/default.jpg" if a.get("image_id") and a.get("is_public_domain") else "",
        "openImage": bool(a.get("is_public_domain")),
        "url": f"https://www.artic.edu/artworks/{a['id']}",
        "dataLicence": "CC0 (description field CC-BY)", "matchBasis": "place_of_origin: " + (a.get("place_of_origin") or ""),
        "lqip": ((a.get("thumbnail") or {}).get("lqip") or ""), "alt": ((a.get("thumbnail") or {}).get("alt_text") or "")})

# ---------------------------------------------------------------- Metropolitan Museum of Art (Open Access, CC0 for public-domain works)
print("Met …")
ids = (get("https://collectionapi.metmuseum.org/public/collection/v1/search?geoLocation=Nepal&q=*") or {}).get("objectIDs") or []
met_raw = []
def met_one(oid):
    time.sleep(0.15)
    return get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
with ThreadPoolExecutor(4) as ex:
    for d in ex.map(met_one, ids):
        if not d or not d.get("objectID"):
            continue
        met_raw.append(d)
        geo = " ".join([d.get("country", ""), d.get("culture", ""), d.get("region", ""), d.get("geographyType", "")])
        objects.append({
            "source": "Metropolitan Museum of Art", "country": "USA", "id": f"met-{d['objectID']}",
            "title": d.get("title") or d.get("objectName") or "Untitled", "date": d.get("objectDate") or "",
            "type": d.get("classification") or d.get("objectName") or "", "medium": d.get("medium") or "",
            "place": d.get("culture") or d.get("country") or "", "accession": d.get("accessionNumber") or "",
            "credit": d.get("creditLine") or "", "provenance": "",
            "image": d.get("primaryImageSmall") if d.get("isPublicDomain") else "",
            "openImage": bool(d.get("isPublicDomain")), "url": d.get("objectURL") or "",
            "dataLicence": "CC0 (Open Access)" if d.get("isPublicDomain") else "Metadata via API; image rights reserved",
            "matchBasis": "geoLocation=Nepal" + ("" if "nepal" in geo.lower() else " (Nepal not in culture/country field — check)")})
json.dump(met_raw, open(RAW / "met.json", "w"), indent=1)

# ---------------------------------------------------------------- Cleveland Museum of Art (CC0 open access)
print("Cleveland …")
cma = get("https://openaccess-api.clevelandart.org/api/artworks/?culture=Nepal&limit=1000")
json.dump(cma, open(RAW / "cleveland.json", "w"), indent=1)
for a in (cma or {}).get("data", []):
    cultures = " ".join(a.get("culture") or [])
    if "nepal" not in cultures.lower():
        continue  # API culture filter is fuzzy; keep only records naming Nepal
    img = ((a.get("images") or {}).get("web") or {}).get("url") or ""
    objects.append({
        "source": "Cleveland Museum of Art", "country": "USA", "id": f"cma-{a['id']}",
        "title": a.get("title") or "", "date": a.get("creation_date") or "", "type": a.get("type") or "",
        "medium": a.get("technique") or "", "place": cultures, "accession": a.get("accession_number") or "",
        "credit": a.get("creditline") or "",
        "provenance": clean("; ".join(f"{p.get('description','')} {p.get('date','') or ''}".strip() for p in (a.get("provenance") or [])), 900),
        "image": img if a.get("share_license_status") == "CC0" else "",
        "openImage": a.get("share_license_status") == "CC0", "url": a.get("url") or "",
        "dataLicence": a.get("share_license_status") or "", "matchBasis": "culture field contains 'Nepal'"})

# ---------------------------------------------------------------- Victoria and Albert Museum
print("V&A …")
va_recs, page = [], 1
while True:
    r = get(f"https://api.vam.ac.uk/v2/objects/search?q_place_name=Nepal&page_size=100&page={page}")
    if not r or not r.get("records"):
        break
    va_recs += r["records"]
    if page >= r["info"]["pages"]:
        break
    page += 1
def va_one(rec):
    time.sleep(0.1)
    d = get(f"https://api.vam.ac.uk/v2/object/{rec['systemNumber']}")
    return rec, (d or {}).get("record", {})
va_full = []
with ThreadPoolExecutor(6) as ex:
    for rec, full in ex.map(va_one, va_recs):
        va_full.append(full)
        title = (full.get("titles") or [{}])[0].get("title") if full.get("titles") else ""
        objects.append({
            "source": "Victoria and Albert Museum", "country": "UK", "id": f"vam-{rec['systemNumber']}",
            "title": title or full.get("briefDescription") or rec.get("objectType") or "Untitled",
            "date": rec.get("_primaryDate") or "", "type": rec.get("objectType") or "",
            "medium": full.get("materialsAndTechniques") or "", "place": rec.get("_primaryPlace") or "",
            "accession": rec.get("accessionNumber") or "", "credit": full.get("creditLine") or "",
            "provenance": clean(full.get("objectHistory"), 900),
            "image": (rec.get("_images") or {}).get("_iiif_image_base_url", "") + "full/!400,400/0/default.jpg" if (rec.get("_images") or {}).get("_iiif_image_base_url") else "",
            "openImage": False,
            "url": f"https://collections.vam.ac.uk/item/{rec['systemNumber']}/",
            "dataLicence": "V&A API — check V&A terms before reuse",
            "matchBasis": "place name Nepal (" + ("primary place" if "nepal" in (rec.get("_primaryPlace") or "").lower() else "secondary/associated place — check") + ")"})
json.dump(va_full, open(RAW / "vam.json", "w"), indent=1)

# ---------------------------------------------------------------- Wellcome Collection
print("Wellcome …")
wc_recs, url = [], "https://api.wellcomecollection.org/catalogue/v2/works?query=Nepal&pageSize=100&include=production,subjects"
while url:
    r = get(url)
    if not r:
        break
    wc_recs += r.get("results", [])
    url = r.get("nextPage")
json.dump(wc_recs, open(RAW / "wellcome.json", "w"), indent=1)
for w in wc_recs:
    places = [p.get("label", "") for pe in (w.get("production") or []) for p in (pe.get("places") or [])]
    dates = [d.get("label", "") for pe in (w.get("production") or []) for d in (pe.get("dates") or [])]
    lic = ((w.get("thumbnail") or {}).get("license") or {}).get("label", "")
    objects.append({
        "source": "Wellcome Collection", "country": "UK", "id": f"wc-{w['id']}",
        "title": w.get("title") or "", "date": ", ".join(dates), "type": (w.get("workType") or {}).get("label", ""),
        "medium": w.get("physicalDescription") or "", "place": ", ".join(places),
        "accession": w.get("referenceNumber") or "", "credit": "", "provenance": "",
        "image": (w.get("thumbnail") or {}).get("url", ""),
        "openImage": lic in ("Public Domain Mark", "CC0", "Attribution 4.0 International (CC BY 4.0)"),
        "url": f"https://wellcomecollection.org/works/{w['id']}",
        "dataLicence": ("Image: " + lic) if lic else "See record",
        "matchBasis": "keyword 'Nepal'" + (" (production place Nepal)" if any("nepal" in p.lower() for p in places) else " — relevance not guaranteed")})


# ---------------------------------------------------------------- Harvard Art Museums (requires free API key)
# Set the key in your shell, never in this file:  export HARVARD_API_KEY=...
import os
HKEY = os.environ.get("HARVARD_API_KEY")
if not HKEY:
    print("Harvard … skipped (set HARVARD_API_KEY to include)")
else:
    print("Harvard …")
    hv = {}
    # IDs looked up via the /place and /culture endpoints on 16 Sep 2026
    for flt in ("place=2035424", "culture=37528164"):
        page = 1
        while True:
            r = get(f"https://api.harvardartmuseums.org/object?apikey={HKEY}&{flt}&size=100&page={page}")
            if not r or not r.get("records"):
                break
            for rec in r["records"]:
                rec.setdefault("_matched", []).append(flt)
                if rec["id"] in hv:
                    hv[rec["id"]]["_matched"].append(flt)
                else:
                    hv[rec["id"]] = rec
            if page >= r["info"]["pages"]:
                break
            page += 1
    json.dump(list(hv.values()), open(RAW / "harvard.json", "w"), indent=1)
    for rec in hv.values():
        img = rec.get("primaryimageurl") or ""
        objects.append({
            "source": "Harvard Art Museums", "country": "USA", "id": f"ham-{rec['id']}",
            "title": rec.get("title") or "Untitled", "date": rec.get("dated") or rec.get("century") or "",
            "type": rec.get("classification") or "", "medium": rec.get("medium") or "",
            "place": rec.get("culture") or "", "accession": rec.get("objectnumber") or "",
            "credit": rec.get("creditline") or "", "provenance": clean(rec.get("provenance"), 900),
            # imagepermissionlevel 0 is taken to mean the image may be shown; verify against Harvard's API docs
            "image": (img + "?width=400") if img and rec.get("imagepermissionlevel") == 0 else "",
            "openImage": rec.get("imagepermissionlevel") == 0 and bool(img),
            "url": rec.get("url") or "",
            "dataLicence": "Harvard Art Museums API — check Harvard API terms before reuse",
            "matchBasis": " + ".join(sorted(set("place Nepal" if "place" in m else "culture Nepalese" for m in rec["_matched"])))})

NEPAL_TERMS = re.compile(r"nepal|nipal|kathmandu|katmandu|patan|bhaktapur|lalitpur|gurkha|gorkha|newar|sherpa|licchavi|malla", re.I)
for o in objects:
    o["century"] = century_bucket(o["date"])
    weak = ("check" in o["matchBasis"] or "not guaranteed" in o["matchBasis"]) and not NEPAL_TERMS.search(o["title"] + " " + o["place"])
    o["strength"] = "weak" if weak else "strong"

# log Met IDs that the search index returned but whose object records 404
met_ok = {str(d["objectID"]) for d in met_raw}
missing = [i for i in ids if str(i) not in met_ok]
json.dump({"harvested": time.strftime("%Y-%m-%d"), "met_ids_returned_404": missing},
          open(ROOT / "data" / "harvest_log.json", "w"), indent=1)

json.dump(objects, open(ROOT / "data" / "objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(o["source"] for o in objects))
print("total", len(objects))
