#!/usr/bin/env python3
"""
Import British Museum collection data for the catalogue.

Accepts either:
  - the British Museum's own "download results" CSV from Collection online (preferred; 47 columns incl. acquisition)
  - the CSV produced by scripts/bm_export_console.js
Used with the British Museum's permission. Licence: CC BY-NC-SA 4.0, "© The Trustees of the British Museum".
Output: data/bm_objects.json (kept separate from the CC0 data).

Run:  python3 scripts/import_bm.py data/raw/bm_export_2026-09-21.csv
"""
import csv, json, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = pathlib.Path(sys.argv[1])
NEPAL = re.compile(r"\b(nepal\w*|kathmandu|katmandu|bhaktapur|lalitpur|patan \(nepal\)|newar\w*|sherpa|tharu|gurung|tamang|magar|limbu|thakali|licchavi|malla|rai)\b", re.I)
# Department -> object URL prefix. Verified against live object links on 21 Sep 2026 for these two only.
DEPT_PREFIX = {"Asia": "A", "Money and Medals": "C"}
LICENCE = "CC BY-NC-SA 4.0 — © The Trustees of the British Museum (used with permission)"


def museum_number(v):
    m = re.search(r"Optional\[(.*)\]", v or "")
    return (m.group(1) if m else (v or "")).strip()


def slug(n):
    return re.sub(r"[,. ]", "-", n.replace("+", ""))


def clip(s, n):
    s = re.sub(r"\s+", " ", (s or "").strip().strip(";").strip())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def join(*parts, sep="; "):
    return sep.join(p for p in (x.strip() for x in parts if x) if p)


rows = list(csv.DictReader(open(src, encoding="utf-8-sig", newline="")))
official = "Dept" in rows[0]
out, seen = [], {}
for r in rows:
    if official:
        num = museum_number(r.get("Museum number"))
        dept = r.get("Dept", "")
        otype = re.sub(r"\s*\(object name\)", "", r.get("Object type", "") or "")
        title = r.get("Title") or otype or "Untitled"
        place = join(r.get("Production place", ""), r.get("Find spot", ""))
        people = join(r.get("Ethnic name (made by)", ""), r.get("Culture", ""), r.get("Authority", ""))
        acq, prev = r.get("Acq name (acq)", ""), r.get("Acq name (previous)", "")
        provenance = join(acq, ("Acquired " + r["Acq date"]) if r.get("Acq date") else "",
                          ("Previously: " + prev) if prev and prev != acq else "",
                          r.get("Acq notes (acq)", ""), sep=". ")
        pref = DEPT_PREFIX.get(dept)
        url = (f"https://www.britishmuseum.org/collection/object/{pref}_{slug(num)}" if pref
               else "https://www.britishmuseum.org/collection/search?keyword=" + urllib.parse.quote(num))
        rec = {"title": title[:1].upper() + title[1:], "date": r.get("Production date", ""), "type": otype.split(";")[0].strip(),
               "medium": r.get("Materials", ""), "place": place, "accession": num, "credit": people,
               "provenance": clip(provenance, 900), "description": clip(r.get("Description", ""), 400),
               "image": r.get("Image", "") or "", "url": url, "dept": dept}
        placeish = " ".join([place, people, r.get("Ethnic name (assoc)", "")])
    else:  # console-export format
        num = r.get("Museum number", "")
        rec = {"title": r.get("title") or "Untitled", "date": r.get("Production date", ""),
               "type": (r.get("title") or "").split(";")[0].strip(), "medium": r.get("Materials", ""),
               "place": join(r.get("Production place", ""), r.get("Findspot", "")), "accession": num,
               "credit": join(r.get("Ethnic group", ""), r.get("Cultures/periods", ""), r.get("Authority", "")),
               "provenance": "", "description": "", "image": "", "url": r.get("url", ""), "dept": ""}
        placeish = rec["place"] + " " + rec["credit"]
    key = slug(num) or f"row{len(out)}"
    seen[key] = seen.get(key, 0) + 1
    oid = "bm-" + key + (f"-{seen[key]}" if seen[key] > 1 else "")
    strong = bool(NEPAL.search(placeish) or NEPAL.search(rec["title"]))
    rec.update({"source": "British Museum", "country": "UK", "id": oid,
                "openImage": False,  # CC BY-NC-SA, shown from the Museum's server with credit, not copied
                "dataLicence": LICENCE,
                "matchBasis": "Nepal in production place, findspot, ethnic group, culture or ruler" if strong
                              else "Keyword 'nepal' only — not Nepalese by place fields; check",
                "strength": "strong" if strong else "weak"})
    out.append(rec)

json.dump(out, open(ROOT / "data" / "bm_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(f"{len(out)} records from {'official export' if official else 'console export'}; "
      f"{Counter(o['strength'] for o in out)}; with image {sum(bool(o['image']) for o in out)}; "
      f"with provenance {sum(bool(o['provenance']) for o in out)}")
