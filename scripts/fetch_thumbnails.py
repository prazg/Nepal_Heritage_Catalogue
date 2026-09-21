#!/usr/bin/env python3
"""
Download small copies of OPENLY LICENSED images into images/thumbs/ so the site
does not depend on other servers allowing hotlinking.

Why: several image servers now block embedding on other websites. On 16 Sep 2026
the Art Institute of Chicago's IIIF server returned 403 with a Cloudflare challenge
and `Cross-Origin-Resource-Policy: same-origin` (see
github.com/art-institute-of-chicago/data-aggregator/issues/151).

What is copied (open licences only):
  - Met Open Access (CC0), Cleveland (CC0), Smithsonian Open Access (CC0)
  - Wellcome images marked Public Domain Mark, CC0 or CC BY 4.0 (attribution shown on site)
  - Art Institute of Chicago public-domain images (CC0) — attempted politely, may be blocked
  - LACMA public-domain images (released by LACMA without restriction)
Not copied (reuse terms less clear, so the site links to them instead):
  - Victoria and Albert Museum, Harvard Art Museums

Politeness: identifies itself, runs slowly, skips files already downloaded.
Chicago's guidelines ask for one image at a time with a 1-second delay; that is followed.

Run:  python3 scripts/fetch_thumbnails.py
Requires: Pillow  (pip install Pillow)
"""
import io, json, pathlib, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "thumbs"
OUT.mkdir(parents=True, exist_ok=True)
MAX_SIDE = 480
UA = {"User-Agent": "nepal-heritage-abroad/1.0 (non-commercial research catalogue; thumbnails of open-licence images)"}

SELF_HOST = {"Metropolitan Museum of Art", "Cleveland Museum of Art", "Wellcome Collection", "Art Institute of Chicago", "Los Angeles County Museum of Art"}
WELLCOME_OK = ("Public Domain Mark", "CC0", "Attribution 4.0 International (CC BY 4.0)")


def eligible(o):
    if not (o.get("image") and o.get("openImage")):
        return False
    if o["source"].startswith("Smithsonian"):
        return True
    if o["source"] == "Wellcome Collection":
        return any(k in (o.get("dataLicence") or "") for k in WELLCOME_OK)
    return o["source"] in SELF_HOST


def fetch(o):
    dest = OUT / f"{o['id']}.jpg"
    if dest.exists():
        return o["id"], "exists"
    url = o["image"]
    if o["source"] == "Smithsonian" or o["source"].startswith("Smithsonian"):
        url += ("&" if "?" in url else "?") + "max=600"  # smaller rendition; falls back to full if ignored
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        im.save(dest, "JPEG", quality=78, optimize=True, progressive=True)
        return o["id"], "ok"
    except urllib.error.HTTPError as e:
        return o["id"], f"http {e.code}"
    except Exception as e:
        return o["id"], f"error {type(e).__name__}"


objects = json.load(open(ROOT / "data" / "objects.json"))
for extra in ("smithsonian_objects.json", "lacma_objects.json"):
    pth = ROOT / "data" / extra
    if pth.exists():
        objects += json.load(open(pth))
todo = [o for o in objects if eligible(o)]
aic = [o for o in todo if o["source"] == "Art Institute of Chicago"]
rest = [o for o in todo if o["source"] != "Art Institute of Chicago"]
results = {}

print(f"{len(rest)} images from Met, Cleveland, Wellcome, Smithsonian …")
def slow(o):
    r = fetch(o)
    time.sleep(0.3)
    return r
with ThreadPoolExecutor(3) as ex:
    for i, (oid, status) in enumerate(ex.map(slow, rest), 1):
        results[oid] = status
        if i % 100 == 0:
            print(f"  {i}/{len(rest)}")

print(f"{len(aic)} Art Institute of Chicago images, one at a time …")
for i, o in enumerate(aic, 1):
    oid, status = fetch(o)
    results[oid] = status
    if i <= 3 and status.startswith("http 403"):
        print("  Chicago's server is refusing requests from this connection (403). Stopping Chicago downloads.")
        for rest_o in aic[i:]:
            results[rest_o["id"]] = "skipped after 403"
        break
    time.sleep(1.0)

have = sorted(p.stem for p in OUT.glob("*.jpg"))
json.dump(have, open(ROOT / "data" / "thumbs.json", "w"))
from collections import Counter
print(Counter(s if not s.startswith("http") else s for s in results.values()))
print(f"{len(have)} thumbnails available; total size {sum(p.stat().st_size for p in OUT.glob('*.jpg'))/1e6:.1f} MB")
