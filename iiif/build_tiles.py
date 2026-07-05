"""Generate a IIIF Image API 3 *level-0* static tile hierarchy per plate.

For each plate JPEG in ``iiif/pages/`` we produce:

    iiif/tiles/<id>/
        info.json
        full/<w>,/0/default.jpg           (whole-image size variants)
        <region>/<w>,<h>/0/default.jpg    (tile region derivatives)

Level 0 static compliance means every rendered variant is precomputed as a
static file at a URL that mirrors the Image API request grammar; the server
only ever needs to serve bytes. See:

    https://iiif.io/api/image/3.0/compliance/  (Level 0)
    https://iiif.io/api/image/3.0/#4-image-requests

We produce:

- ``full`` variants at sizes: [max, 1024, 512, 256] (widths of the whole image;
  height is derived, aspect-preserving)
- A single scale-factor 1 tile grid of 512x512 tiles under
  ``<x>,<y>,<w>,<h>/<w>,<h>/0/default.jpg`` -- this is what Clover / OSD
  request when deep-zooming.

Level 0 servers advertise ``sizes`` and ``tiles`` blocks in info.json; both
are populated here so the viewer can render smoothly without probing.

Usage:
    python iiif/build_tiles.py
    python iiif/build_tiles.py --base https://iiif.example.org/iiif
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGES = REPO_ROOT / "iiif" / "pages"
DEFAULT_TILES = REPO_ROOT / "iiif" / "tiles"
DEFAULT_BASE = "https://REPLACE-ME.example.org/iiif"

# Whole-image width variants (px). The rendered plate is ~1700 wide, so the
# "max" variant equals the source width; the smaller sizes give the viewer
# thumbnails and mid-zoom levels.
FULL_WIDTHS = [1024, 512, 256]

# Tile size for the level-0 tile grid. Clover / OpenSeadragon default to
# either 256 or 512 tiles; 512 gives fewer files with comparable quality.
TILE_SIZE = 512
JPEG_QUALITY = 85


def _open_source(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def _write_jpeg(img: Image.Image, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)


def build_tiles_for_plate(
    src: Path,
    plate_id: str,
    tiles_root: Path,
    base_url: str,
) -> dict:
    """Emit level-0 static assets for one plate. Returns its info.json dict."""
    img = _open_source(src)
    w, h = img.size

    plate_dir = tiles_root / plate_id
    plate_dir.mkdir(parents=True, exist_ok=True)

    sizes: list[dict[str, int]] = []

    # 1) `full/max` -- the identity variant. Image API 3 uses `max` (not
    # `full`) for the size segment.
    full_max = plate_dir / "full" / "max" / "0" / "default.jpg"
    _write_jpeg(img, full_max)
    sizes.append({"width": w, "height": h})

    # 2) whole-image derivative widths
    for target_w in FULL_WIDTHS:
        if target_w >= w:
            continue
        target_h = round(h * (target_w / w))
        resized = img.resize((target_w, target_h), Image.LANCZOS)
        out = plate_dir / "full" / f"{target_w},{target_h}" / "0" / "default.jpg"
        _write_jpeg(resized, out)
        sizes.append({"width": target_w, "height": target_h})

    # 3) tile grid at scale factor 1
    tile_count = 0
    tiles_x = math.ceil(w / TILE_SIZE)
    tiles_y = math.ceil(h / TILE_SIZE)
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            x = tx * TILE_SIZE
            y = ty * TILE_SIZE
            tw = min(TILE_SIZE, w - x)
            th = min(TILE_SIZE, h - y)
            crop = img.crop((x, y, x + tw, y + th))
            # URL grammar: {region}/{size}/{rotation}/{quality}.{format}
            region = f"{x},{y},{tw},{th}"
            size = f"{tw},{th}"
            out = plate_dir / region / size / "0" / "default.jpg"
            _write_jpeg(crop, out)
            tile_count += 1

    # 4) info.json (Image API 3.0)
    image_id = f"{base_url.rstrip('/')}/{plate_id}"
    info = {
        "@context": "http://iiif.io/api/image/3/context.json",
        "id": image_id,
        "type": "ImageService3",
        "protocol": "http://iiif.io/api/image",
        "profile": "level0",
        "width": w,
        "height": h,
        "sizes": sizes,
        "tiles": [
            {"width": TILE_SIZE, "height": TILE_SIZE, "scaleFactors": [1]}
        ],
        "extraFormats": ["jpg"],
        "extraQualities": ["default"],
        "extraFeatures": [],
    }
    info_path = plate_dir / "info.json"
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    return {
        "plate_id": plate_id,
        "width": w,
        "height": h,
        "sizes": len(sizes),
        "tiles_written": tile_count,
        "info_json": info_path,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pages", default=str(DEFAULT_PAGES),
                   help="Directory holding plate_NN.jpg source renders")
    p.add_argument("--out", default=str(DEFAULT_TILES),
                   help="Output tiles root directory")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help="Public base URL under which /<plate_id> will resolve")
    args = p.parse_args(argv)

    pages_dir = Path(args.pages)
    tiles_root = Path(args.out)

    plates = sorted(pages_dir.glob("plate_*.jpg"))
    if not plates:
        print(f"ERROR: no plate JPEGs found in {pages_dir}. "
              f"Run iiif/extract_plates.py first.", file=sys.stderr)
        return 2

    tiles_root.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for src in plates:
        plate_id = src.stem  # e.g. "plate_01"
        info = build_tiles_for_plate(src, plate_id, tiles_root, args.base)
        summary.append({k: (str(v) if isinstance(v, Path) else v)
                        for k, v in info.items()})
        print(f"  {plate_id}: {info['width']}x{info['height']}, "
              f"{info['sizes']} full-sizes, {info['tiles_written']} tiles")

    idx = tiles_root / "index.json"
    idx.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"Wrote tile index -> {idx}")
    total_tiles = sum(s["tiles_written"] for s in summary)
    print(f"Done. {len(summary)} plates, {total_tiles} tile files total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
