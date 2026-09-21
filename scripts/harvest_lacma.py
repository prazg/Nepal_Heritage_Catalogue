#!/usr/bin/env python3
"""
Harvest Nepal-related objects from LACMA via collections.lacma.org.

collections.lacma.org's robots.txt allows all automated access (checked 21 Sep 2026).
This uses the same POST /api/search endpoint the site's own search page calls
(request/response shape observed in the browser on 21 Sep 2026; it is not a documented public API,
so it may change without notice). www.lacma.org is NOT used — its robots rules restrict automated access.

Politeness: identifies itself, one request at a time, 1.5 s apart.
Output: data/raw/lacma.json and data/lacma_objects.json

Run:  python3 scripts/harvest_lacma.py
"""
import json, pathlib, re, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://collections.lacma.org/api/search"
UA = "nepal-heritage-abroad/1.0 (non-commercial research catalogue)"
QUERIES = ["nepal", "kathmandu", "newar", "bhaktapur", "patan", "lalitpur"]
NEPAL = re.compile(r"\bnepal|kathmandu|bhaktapur|lalitpur|patan\b|\bnewar", re.I)
PER_PAGE = 48


def search(query, page, public_domain=False):
    body = {"query": query, "classification": [], "department": [], "artist": [], "placeMade": [], "creditLine": [],
            "culture": [], "period": [], "style": [], "building": [], "gallery": [], "onView": False,
            "hasImage": False, "publicDomain": public_domain, "sort": "RELEVANCE", "page": page, "perPage": PER_PAGE}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            print(f"  retry {attempt + 1} ({e})")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed: {query} page {page}")


def run(query, public_domain=False):
    out, page = {}, 1
    while True:
        d = search(query, page, public_domain)
        for r in d.get("results", []):
            out[r["id"]] = r
        total = d.get("total", 0)
        if page * PER_PAGE >= total or not d.get("results"):
            break
        page += 1
        time.sleep(1.5)
    time.sleep(1.5)
    return out, total


found = {}
for q in QUERIES:
    res, total = run(q)
    new = len(set(res) - set(found))
    found.update(res)
    print(f"'{q}': {total} results, {new} new (running total {len(found)})")

pd_ids = set()
for q in QUERIES:
    res, total = run(q, public_domain=True)
    pd_ids |= set(res)
print(f"public-domain subset: {len(pd_ids)}")

json.dump({"results": list(found.values()), "public_domain_ids": sorted(pd_ids)}, open(ROOT / "data" / "raw" / "lacma.json", "w"))

objects = []
for oid, r in found.items():
    o = (r.get("data") or {}).get("object") or {}
    titles = sorted(o.get("titles") or [], key=lambda t: t.get("displayOrder", 99))
    title = (titles[0]["title"] if titles else "Untitled").strip()
    places = o.get("placeMade") or []
    culture = o.get("culture") or ""
    artists = "; ".join(c.get("displayName", "") for c in (o.get("constituents") or []) if c.get("displayName") and c.get("displayName") != "Unknown")
    placeish = " ".join(places) + " " + (culture if isinstance(culture, str) else " ".join(culture or []))
    strong = bool(NEPAL.search(placeish)) and not re.search(r"\bIndia\b", placeish)
    imgs = sorted(o.get("images") or [], key=lambda i: i.get("displayOrder", 99))
    rend = (imgs[0].get("renditions") or {}) if imgs else {}
    is_pd = oid in pd_ids
    objects.append({
        "source": "Los Angeles County Museum of Art", "country": "USA", "id": f"lacma-{oid}",
        "title": title, "date": o.get("dated") or "", "type": o.get("classification") or "",
        "medium": o.get("medium") or "", "place": "; ".join(places),
        "accession": o.get("accessionNumber") or "", "credit": "; ".join(x for x in [o.get("creditLine") or "", artists] if x),
        "provenance": "", "description": o.get("department") or "",
        # Public-domain images: LACMA releases these without restriction. Others: shown from LACMA's server for identification.
        "image": rend.get("desktop") or rend.get("primary") or "",
        "openImage": bool(is_pd and (rend.get("desktop") or rend.get("primary"))),
        "url": f"https://collections.lacma.org/object/{oid}",
        "dataLicence": "LACMA collections website; public-domain image" if is_pd else "LACMA collections website; image rights reserved by LACMA",
        "matchBasis": "Place made: " + "; ".join(places) if strong else "Keyword match only (place made: " + ("; ".join(places) or "not given") + ") — check",
        "strength": "strong" if strong else "weak",
    })

json.dump(objects, open(ROOT / "data" / "lacma_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(objects), "objects;", Counter(o["strength"] for o in objects), "; open images", sum(o["openImage"] for o in objects))
