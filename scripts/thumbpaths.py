"""
Single source of truth for where thumbnail files live.

GitHub's web interface shows at most 1,000 files per folder, so thumbnails are split into one
subfolder per source (the record id prefix: met, cma, wc, si, lacma, ...). If a source ever grows
past MAX_PER_FOLDER images, its folder is split again into 16 subfolders by a hash of the record id.

Used by fetch_thumbnails.py (where to save) and build_data.py (what URL the site uses).
"""
import hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
THUMBS = ROOT / "images" / "thumbs"
MAX_PER_FOLDER = 900


def _prefix(record_id):
    return record_id.split("-", 1)[0]


def rel_path(record_id, source_count):
    """Path relative to the site root, e.g. 'images/thumbs/met/met-38536.jpg'."""
    p = _prefix(record_id)
    if source_count > MAX_PER_FOLDER:
        return f"images/thumbs/{p}/{hashlib.md5(record_id.encode()).hexdigest()[0]}/{record_id}.jpg"
    return f"images/thumbs/{p}/{record_id}.jpg"


def counts(record_ids):
    out = {}
    for r in record_ids:
        out[_prefix(r)] = out.get(_prefix(r), 0) + 1
    return out
