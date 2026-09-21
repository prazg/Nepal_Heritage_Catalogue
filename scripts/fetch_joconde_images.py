#!/usr/bin/env python3
"""
Read image references (IMG), diffusion flag (DIFFU) and photo credit (COPY) for each Joconde record
from its POP page (pop.culture.gouv.fr/notice/joconde/<REF>), 1.5 s apart.
Output: data/raw/joconde_pop_images.json — used by import_joconde.py.

Images live at https://popcorn-prd-perf-assets.s3.gra.io.cloud.ovh.net/<IMG path>.
POP's terms: photographs may be under copyright and need the rights holders' prior permission,
so the site shows them only when data/settings.json has live_images.joconde.on = true.
Records with DIFFU = "non" are never shown.

Run:  python3 scripts/fetch_joconde_images.py
"""
import json, pathlib, re, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "nepal-heritage-abroad/1.0 (non-commercial research catalogue)"}
recs = json.load(open(ROOT / "data" / "joconde_objects.json"))
out = {}
for o in recs:
    ref = o["id"][3:]
    try:
        h = urllib.request.urlopen(urllib.request.Request(f"https://pop.culture.gouv.fr/notice/joconde/{ref}", headers=UA), timeout=60).read().decode("utf-8", "replace").replace('\\"', '"')
    except Exception as e:
        print("!", ref, e)
        continue

    def grab(k):
        m = re.search(r'"%s":(\[[^\]]*\]|"[^"]*")' % k, h)
        return json.loads(m.group(1)) if m else None

    out[ref] = {"IMG": grab("IMG"), "DIFFU": grab("DIFFU"), "COPY": grab("COPY"), "PHOT": grab("PHOT")}
    time.sleep(1.5)
json.dump(out, open(ROOT / "data" / "raw" / "joconde_pop_images.json", "w"), indent=1, ensure_ascii=False)
print(len(out), "records;", sum(bool(v["IMG"]) for v in out.values()), "with images")
