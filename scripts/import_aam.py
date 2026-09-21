#!/usr/bin/env python3
"""
Import Asian Art Museum (San Francisco) records from a saved eMuseum results page.

Why a saved page: searchcollection.asianart.org sits behind an AWS WAF bot challenge, so the
search is run and saved ("Webpage, HTML only") in a normal browser, then parsed here.
The saved search (21 Sep 2026): Place of Origin = Nepal; Department = Himalayan Art (92 results).

Run:  python3 scripts/import_aam.py data/raw/aam_nepal_himalayan_2026-09-21.html [more.html ...]
Output: data/aam_objects.json
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = re.compile(r'<div class="texts-wrap">(.*?)(?=<div class="texts-wrap">|<!-- 1\. Result Tools|</main>|$)', re.S)
TITLE = re.compile(r'<a href="(https://searchcollection\.asianart\.org/objects/(\d+)/[^"?]*)[^"]*"[^>]*>\s*(.*?)\s*</a>', re.S)
FIELD = re.compile(r'<div class="text-wrap">(?:<span>([^<:]+):\s*</span>)?(.*?)</div>', re.S)


def text(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


out = {}
for path in sys.argv[1:]:
    h = open(path, encoding="utf-8", errors="replace").read()
    for blk in BLOCK.findall(h):
        m = TITLE.search(blk)
        if not m:
            continue
        url, oid, title = m.group(1), m.group(2), text(m.group(3))
        fields, makers = {}, []
        for label, value in FIELD.findall(blk[m.end():]):
            v = text(value)
            if not v:
                continue
            if label:
                fields[label.strip()] = v
            else:
                makers.append(v)
        out[oid] = {
            "source": "Asian Art Museum, San Francisco", "country": "USA", "id": f"aam-{oid}",
            "title": title, "date": fields.get("Date", ""), "type": "", "medium": fields.get("Materials", ""),
            "place": "Nepal", "accession": fields.get("Object number", ""), "credit": "; ".join(makers),
            "provenance": "", "description": "", "image": "", "openImage": False, "url": url,
            "dataLicence": "Asian Art Museum collection website (image rights not established; images not reproduced)",
            "matchBasis": "Museum search: Place of Origin = Nepal, Department = Himalayan Art",
            "strength": "strong",
        }

recs = list(out.values())
json.dump(recs, open(ROOT / "data" / "aam_objects.json", "w"), indent=1, ensure_ascii=False)
print(len(recs), "records;", sum(bool(r["accession"]) for r in recs), "with object number;", sum(bool(r["date"]) for r in recs), "with date")
