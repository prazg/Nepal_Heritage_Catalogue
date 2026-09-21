#!/usr/bin/env python3
"""
Harvest Rubin Museum of Himalayan Art objects in its "Nepalese Regions" group.

1. rubinmuseum.org's WordPress REST API lists collection objects by region
   (/wp-json/wp/v2/collection?region=49 — term 49 = "Nepalese Regions", checked 21 Sep 2026).
2. Each object page's "Artwork Details" block gives title, medium, origin, date, credit line,
   object number and HAR number. robots.txt allows general crawlers on these pages.
Politeness: identifies itself; one request at a time, 2 s apart. Images are not reproduced.

Run:  python3 scripts/harvest_rubin.py
Output: data/raw/rubin.json, data/rubin_objects.json
"""
import html, json, pathlib, re, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "nepal-heritage-abroad/1.0 (non-commercial research catalogue)"}
REGION_ID = 49
NEPAL = re.compile(r"nepal|kathmandu|bhaktapur|lalitpur|patan|newar", re.I)
LABELS = ["Title", "Dimensions", "Medium", "Origin", "Classification(s)", "Date", "Credit Line",
          "Object number", "HAR Number", "Provenance", "Inscription", "Artist", "Culture", "Period"]


def get(url, as_json=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        body = r.read().decode("utf-8", "replace")
        return (json.loads(body), dict(r.headers)) if as_json else body


# 1. object list
items, page = [], 1
while True:
    data, headers = get(f"https://rubinmuseum.org/wp-json/wp/v2/collection?region={REGION_ID}&per_page=100&page={page}&_fields=id,link,title", as_json=True)
    items += data
    if page >= int(headers.get("X-WP-TotalPages") or headers.get("x-wp-totalpages") or 1):
        break
    page += 1
    time.sleep(2)
print(len(items), "objects listed")

# 2. object pages
raw, objects = [], []
for n, it in enumerate(items, 1):
    time.sleep(2)
    try:
        h = get(it["link"])
    except Exception as e:
        print("  !", it["link"], e)
        continue
    main = re.search(r"<main.*?</main>", h, re.S)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", main.group(0) if main else h, flags=re.S)
    lines = [html.unescape(re.sub(r"\s+", " ", l)).strip() for l in re.sub(r"<[^>]+>", "\n", body).split("\n")]
    lines = [l for l in lines if l]
    f = {}
    if "Artwork Details" in lines:
        seg = lines[lines.index("Artwork Details") + 1:]
        for i, l in enumerate(seg):
            if l in LABELS and i + 1 < len(seg) and seg[i + 1] not in LABELS:
                f[l] = seg[i + 1]
            if l in ("Iconography", "Concepts", "Begin your search..."):
                break
    # first descriptive paragraph (after the "Enlarge" control)
    desc = ""
    if "Enlarge" in lines:
        after = lines[lines.index("Enlarge") + 1:]
        desc = next((l for l in after if len(l) > 80), "")
    raw.append({"link": it["link"], "fields": f, "description": desc})
    origin = f.get("Origin", "")
    strong = bool(NEPAL.search(origin))
    objects.append({
        "source": "Rubin Museum of Himalayan Art", "country": "USA", "id": "rubin-" + it["link"].rstrip("/").rsplit("/", 1)[-1],
        "title": f.get("Title") or html.unescape(it["title"]["rendered"]), "date": f.get("Date", ""),
        "type": f.get("Classification(s)", ""), "medium": f.get("Medium", ""), "place": origin,
        "accession": f.get("Object number") or html.unescape(it["title"]["rendered"]),
        "credit": f.get("Credit Line", ""), "provenance": f.get("Provenance", "")[:900],
        "description": (desc[:400].rsplit(" ", 1)[0] + "…") if len(desc) > 400 else desc,
        "image": "", "openImage": False, "url": it["link"],
        "har": f.get("HAR Number", ""),
        "dataLicence": "Rubin Museum collection website (images not reproduced)",
        "matchBasis": ("Rubin 'Nepalese Regions'; origin: " + origin) if strong
                      else ("Listed under the Rubin's 'Nepalese Regions' but origin given as: " + (origin or "not stated") + " — check"),
        "strength": "strong" if strong else "weak",
    })
    if n % 20 == 0:
        print(f"  {n}/{len(items)}")

# featured images (350 px WordPress "thumbnail" size, full proportions) via the media endpoint
fm, _ = get(f"https://rubinmuseum.org/wp-json/wp/v2/collection?region={REGION_ID}&per_page=100&_fields=link,featured_media", as_json=True)
ids = [str(x["featured_media"]) for x in fm if x.get("featured_media")]
media = {}
for i in range(0, len(ids), 100):
    time.sleep(2)
    batch, _ = get("https://rubinmuseum.org/wp-json/wp/v2/media?per_page=100&_fields=id,source_url,media_details&include=" + ",".join(ids[i:i + 100]), as_json=True)
    media.update({m["id"]: m for m in batch})
link2img = {}
for x in fm:
    m = media.get(x.get("featured_media"))
    if m:
        sz = (m.get("media_details") or {}).get("sizes", {})
        link2img[x["link"]] = (sz.get("thumbnail") or sz.get("medium") or {}).get("source_url") or m.get("source_url", "")
for o in objects:
    o["imageKey"] = "rubin"
    o["imageCandidate"] = link2img.get(o["url"], "")
    o["imageCreditText"] = "Image courtesy of the Rubin Museum of Himalayan Art (www.rubinmuseum.org), shown from the Museum's server for non-commercial educational use."
for o in objects:
    if o["har"]:
        o["harUrl"] = f"https://www.himalayanart.org/items/{o['har']}"
json.dump(raw, open(ROOT / "data" / "raw" / "rubin.json", "w"), indent=1, ensure_ascii=False)
json.dump(objects, open(ROOT / "data" / "rubin_objects.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(objects), "objects;", Counter(o["strength"] for o in objects), "; with HAR number", sum(bool(o["har"]) for o in objects))
