# Nepalese heritage in collections abroad

A static, searchable catalogue of Nepalese objects, manuscripts and archives held outside Nepal, built from institutions' open data, with hand-curated archival collections and a repatriation tracker.

## Publish on GitHub Pages

1. Create a new repository and upload everything in this folder, keeping the structure (`index.html`, `assets/`, `data/`, `scripts/`).
2. In the repository go to **Settings → Pages**, set the source to **Deploy from a branch**, choose `main` and `/ (root)`, and save.
3. The site appears at `https://<your-username>.github.io/<repository-name>/` after a minute or two.

The page also works when opened directly from disk, because the data is loaded as `data/data.js` rather than fetched.

## Refresh the data

Requires Python 3.9+ and no third-party packages. Harvard records need a free API key, supplied through an environment variable so it never lands in the repository:

```bash
export HARVARD_API_KEY=your-key   # optional; Harvard is skipped without it
python3 scripts/harvest.py      # re-queries the open APIs
python3 scripts/harvest_lacma.py         # LACMA via collections.lacma.org (about 1 min)
python3 scripts/harvest_smithsonian.py   # streams ~2.8 GB from the Smithsonian AWS bucket, keeps Nepal matches (roughly 10–15 min)
# python3 scripts/harvest.py      # re-queries the open APIs (takes a few minutes)
python3 scripts/fetch_thumbnails.py      # optional: small copies of openly licensed images (needs Pillow)
python3 scripts/build_data.py   # rebuilds data/data.js and data/objects.csv
```

APIs change without notice. If a harvester fails, check that institution's current API documentation before editing the script.

## What is in `data/`

| File | Contents |
|---|---|
| `objects.json`, `objects.csv` | Harvested object records (one row per record) |
| `curated.json` | Archives, institutions and repatriation entries, entered by hand with source URLs |
| `harvest_log.json` | Harvest date and Met IDs that returned "not found" |
| `raw/` | Unmodified API responses, for checking |
| `data.js` | Generated bundle loaded by the page — do not edit by hand |

## Sources harvested

| Institution | Endpoint | Selection rule |
|---|---|---|
| Art Institute of Chicago | `api.artic.edu/api/v1/artworks/search` | `place_of_origin` matches Nepal, Kathmandu, Patan, Bhaktapur or Lalitpur |
| Metropolitan Museum of Art | `collectionapi.metmuseum.org/public/collection/v1` | `geoLocation=Nepal` |
| Cleveland Museum of Art | `openaccess-api.clevelandart.org/api/artworks/` | `culture=Nepal`, then kept only if the culture field names Nepal |
| Victoria and Albert Museum | `api.vam.ac.uk/v2` | `q_place_name=Nepal` |
| Wellcome Collection | `api.wellcomecollection.org/catalogue/v2/works` | keyword `Nepal`; weak matches flagged |
| Smithsonian Institution | public S3 bucket `smithsonian-open-access` (metadata/edan/<unit>/) | Nepal term in place, culture, geoLocation or title (strong); elsewhere in record (weak) |
| LACMA | `collections.lacma.org/api/search` (the site's own search endpoint; robots.txt allows all; undocumented, may change) | keyword searches for Nepal and Nepalese places; strong if place made is Nepal or a Newar artist |
| Harvard Art Museums | `api.harvardartmuseums.org/object` | `place=2035424` (Nepal) or `culture=37528164` (Nepalese), merged |

## British Museum records

The British Museum asks for permission before text and data mining; this project has that permission (keep the correspondence on file). Its site is protected by Cloudflare, so the export runs in your own browser rather than as a scraper:

Preferred: use Collection online's own download of search results (the 21 Sep 2026 export is in `data/raw/`). Import with `python3 scripts/import_bm.py data/raw/<file>.csv`.

Fallback if the download option is unavailable:

1. Open `https://www.britishmuseum.org/collection/search?keyword=nepal` (or a narrower filtered search).
2. Open the browser console (F12 → Console), paste `scripts/bm_export_console.js`, press Enter. It reads one page every 3 seconds and downloads `bm_nepal.csv`.
3. `python3 scripts/import_bm.py path/to/bm_nepal.csv` then `python3 scripts/build_data.py`.

These records are CC BY-NC-SA 4.0, credit "© The Trustees of the British Museum", and are stored separately in `data/bm_objects.json`. Keep the site non-commercial. Images are displayed from the Museum's server with credit and are not copied into this repository. Object links are built from museum numbers for the Asia and Money and Medals departments (pattern verified); other departments link to a search for the museum number.

## French museums (Joconde)

Joconde is the national catalogue of the Musées de France (Ministère de la Culture, Licence Ouverte / Open Licence 2.0, CSV about 1.1 GB, updated weekly on data.gouv.fr). It includes the Musée Guimet (about 3,203 records) and other French museums.

1. On your own computer: `python3 scripts/filter_joconde.py` — streams the file from data.gouv.fr and writes only Nepal-related rows to `joconde_nepal.csv` (the 1.1 GB file is not saved).
2. `python3 scripts/import_joconde.py data/raw/<pop export>.xlsx joconde_nepal.csv` — accepts POP exports and the filtered CSV together, de-duplicating by Joconde reference.

POP exports only contain the fields searched: a search on author/school (AUTR, PAUT, ATTR, ECOL) misses most objects. Search "Lieu de création / utilisation" (LIEUX) for Népal, or use `filter_joconde.py`, which checks every field.

## Images

- `images/thumbs/` holds small (max 480 px) copies of openly licensed images only: Met Open Access, Cleveland, Smithsonian Open Access (all CC0) and Wellcome images marked Public Domain Mark, CC0 or CC BY 4.0.
- V&A and Harvard images are not copied; the site links to them.
- The Art Institute of Chicago's image server returned 403 with `Cf-Mitigated: challenge` and `Cross-Origin-Resource-Policy: same-origin` when checked on 16 Sep 2026, so its images cannot be shown on other websites. The downloader tries Chicago one image at a time, as Chicago's API guidelines ask, and stops at the first refusal. If it works from your own connection, rerun `build_data.py` and the copies will be used automatically.

## Reuse and caveats

- Reuse terms belong to each institution and can differ per record; each record carries a `dataLicence` note. Check V&A terms before republishing V&A data or images.
- Inclusion in this catalogue says nothing about an object's legal status. Published provenance is reproduced as given; its absence is not evidence either way.
- Repatriation entries summarise published reporting and can go out of date. Follow the linked sources.
- Do not commit API keys. If a key is ever pushed to GitHub, regenerate it with the provider.
- Period filters are derived automatically from free-text dates and are approximate.

## Adding a repatriation link to an object

Edit `CLAIM_LINKS` in `scripts/build_data.py`. Only add a link when a published source identifies that exact object.
