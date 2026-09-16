# Nepalese heritage in collections abroad

A static, searchable catalogue of Nepalese objects, manuscripts and archives held outside Nepal, built from institutions' open data, with hand-curated archival collections and a repatriation tracker.

Link: https://prazg.github.io/Nepal_Heritage_Catalogue/

## Refresh the data

Requires Python 3.9+ and no third-party packages. Harvard records need a free API key, supplied through an environment variable so it never lands in the repository:

```bash
export HARVARD_API_KEY=your-key   # optional; Harvard is skipped without it
python3 scripts/harvest.py      # re-queries the open APIs
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
| Harvard Art Museums | `api.harvardartmuseums.org/object` | `place=2035424` (Nepal) or `culture=37528164` (Nepalese), merged |

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
