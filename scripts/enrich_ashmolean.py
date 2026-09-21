#!/usr/bin/env python3
"""
Enrich Ashmolean records (from import_ashmolean.py) with credit line, acquisition date and image id.

Source: the item endpoint that ashmolean.org/collections-online itself calls
        https://prd-online.glamdigital.io/v2/item/ash-object-<recordId>/full
        (observed in the browser 21 Sep 2026; undocumented, may change).
Images: served by the Ashmolean's IIIF server, dams.ashmus.ox.ac.uk. They are NOT copied.
        The site shows them from the Ashmolean's server at 400 px only when
        data/settings.json has live_images.ashmolean.on = true (permission confirmed 21 Sep 2026).
Credit required on use: "© Ashmolean Museum, University of Oxford", linked to the object page.

Run:  python3 scripts/enrich_ashmolean.py
"""
import json, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "nepal-heritage-abroad/1.0 (non-commercial research catalogue)"}
ITEM = "https://prd-online.glamdigital.io/v2/item/ash-object-{}/full"
IIIF = "https://dams.ashmus.ox.ac.uk/iiif/image/{}/full/{}/0/default.jpg"
# The Ashmolean's IIIF server rejects "!400,400" for some very wide images (HTTP 400, seen 21 Sep 2026),
# so each image is checked once and the first size the server accepts is used.
SIZES = ["!400,400", "400,", "max"]


def working_image(rs_id):
    for size in SIZES:
        url = IIIF.format(rs_id, size)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                if r.status == 200:
                    return url
        except Exception:
            pass
        time.sleep(0.8)
    return ""

path = ROOT / "data" / "ashmolean_objects.json"
objs = json.load(open(path))
raw = {}
for n, o in enumerate(objs, 1):
    rid = o["id"].split("-", 1)[1]
    try:
        with urllib.request.urlopen(urllib.request.Request(ITEM.format(rid), headers=UA), timeout=60) as r:
            d = json.load(r)
    except Exception as e:
        print("  !", rid, e)
        time.sleep(1.5)
        continue
    raw[rid] = {k: d.get(k) for k in ("creditLine", "acquisitionDatePreview", "showImages", "multimedia")}
    credit = (d.get("creditLine") or "").strip()
    acq = (d.get("acquisitionDatePreview") or "").strip()
    o["credit"] = credit or o.get("credit", "")
    o["provenance"] = "; ".join(x for x in [credit, ("Acquisition date: " + acq) if acq and acq not in credit else ""] if x)
    media = [m for m in (d.get("multimedia") or []) if m.get("isPublished") == "Yes" and m.get("mimeType") == "image" and m.get("resourceSpaceId")]
    media.sort(key=lambda m: m.get("thumbnail") != "true")
    o["imageKey"] = "ashmolean"
    o["imageCreditText"] = "Image © Ashmolean Museum, University of Oxford, shown from the Museum's image server with permission."
    o["imageCandidate"] = working_image(media[0]["resourceSpaceId"]) if media and d.get("showImages") == "yes" else ""
    if n % 20 == 0:
        print(f"  {n}/{len(objs)}")
    time.sleep(1.5)

json.dump(raw, open(ROOT / "data" / "raw" / "ashmolean_items.json", "w"), indent=1, ensure_ascii=False)
json.dump(objs, open(path, "w"), indent=1, ensure_ascii=False)
print(len(raw), "items read;", sum(bool(o.get("imageCandidate")) for o in objs), "with images;",
      sum(bool(o.get("provenance")) for o in objs), "with credit/acquisition")
