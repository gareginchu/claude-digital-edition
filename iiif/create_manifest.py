"""Generate the IIIF Presentation API 3.0 manifest for the plates insert.

Reads:
    iiif/pages/captions.json      -- output of extract_plates.py
    iiif/tiles/<plate_id>/info.json (one per canvas)

Writes:
    iiif/manifests/manifest.json  -- Presentation 3.0

Design notes
------------
* One Canvas per plate. label = "Plate <roman> (fol. <arabic>)"; the OCR-ed
  Armenian caption is stored on the canvas metadata block for citation.
* Each Canvas paints ``full/max/0/default.jpg`` via an Annotation whose
  ``body`` links the level-0 Image Service (info.json).
* A thumbnail (256px width variant) is attached per canvas so grid renderers
  such as Clover's browse mode don't have to download full-resolution.
* Rights: plates originate from the Matenadaran (miniatures) and from private
  family archives (portraits). Per CLAUDE.md this material is in-copyright
  in Armenia until at least 2067-12-31 (life+70) and per-image clearance is
  still pending; we set the manifest ``rights`` to InC-RUW and add a
  ``Public visibility`` metadata field marking the pipeline as
  ``pending rights clearance``.
* Content State: canvases carry stable ``id`` values so a IIIF Content State
  URL can pin a specific region. See iiif/README.md for the citation grammar.

The public base URL is a placeholder (`https://REPLACE-ME.example.org/iiif`);
edit ``--base`` or the ``PUBLIC_BASE`` env var before deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGES = REPO_ROOT / "iiif" / "pages"
DEFAULT_TILES = REPO_ROOT / "iiif" / "tiles"
DEFAULT_OUT = REPO_ROOT / "iiif" / "manifests"

DEFAULT_BASE = os.environ.get("PUBLIC_BASE", "https://REPLACE-ME.example.org/iiif")
MANIFEST_BASE = os.environ.get("MANIFEST_BASE", "https://REPLACE-ME.example.org/manifests")
TEI_BASE = os.environ.get("TEI_BASE", "https://REPLACE-ME.example.org/tei")

# Miniature plates (folios XIV-XXIII) map to Matenadaran shelfmarks documented
# in tei/standoff_plates_manuscripts.xml. Each entry is (plate_no -> xml:id).
# Portraits (plates 1-13) have no manuscript register entry.
PLATE_TO_MSDESC: dict[int, str] = {
    14: "ms_matenadaran_10525",
    15: "ms_matenadaran_1913",
    16: "ms_matenadaran_10521",
    17: "ms_matenadaran_10522",
    18: "ms_matenadaran_10520",
    19: "ms_matenadaran_10519",
    20: "ms_matenadaran_10838",
    21: "ms_matenadaran_10908",
    22: "ms_matenadaran_10382",
    23: "ms_matenadaran_10411",
}


def load_captions(pages_dir: Path) -> list[dict]:
    p = pages_dir / "captions.json"
    if not p.exists():
        raise FileNotFoundError(
            f"Missing {p}. Run iiif/extract_plates.py first.")
    return json.loads(p.read_text(encoding="utf-8"))


def choose_thumbnail(sizes: list[dict], target: int = 256) -> dict:
    """Return the size dict closest to and at least `target` px wide, or the
    largest available if none reach the target."""
    candidates = [s for s in sizes if s["width"] >= target]
    if candidates:
        return min(candidates, key=lambda s: s["width"])
    return max(sizes, key=lambda s: s["width"])


def build_manifest(
    pages_dir: Path,
    tiles_dir: Path,
    base_url: str,
    manifest_id: str,
) -> dict:
    captions = load_captions(pages_dir)
    canvases: list[dict] = []

    for c in captions:
        plate_id = f"plate_{c['plate_no']:02d}"
        info_path = tiles_dir / plate_id / "info.json"
        if not info_path.exists():
            raise FileNotFoundError(
                f"Missing {info_path}. Run iiif/build_tiles.py first.")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        w = info["width"]
        h = info["height"]
        image_svc_id = info["id"]  # e.g. https://.../iiif/plate_01
        canvas_id = f"{base_url.rstrip('/')}/canvas/{plate_id}"
        anno_page_id = f"{canvas_id}/page/1"
        anno_id = f"{canvas_id}/annotation/1"

        # Thumbnail: pick a small precomputed size and reference its file URL.
        thumb = choose_thumbnail(info["sizes"], target=256)
        if thumb["width"] == w:
            thumb_seg = "max"
        else:
            thumb_seg = f"{thumb['width']},{thumb['height']}"
        thumb_url = f"{image_svc_id}/full/{thumb_seg}/0/default.jpg"

        # Human-friendly Armenian label + Roman folio marker.
        label_en = f"Plate {c['plate_no']} (fol. {c['roman']})"
        label_hy = f"Աղյուսակ {c['plate_no']} (թերթ {c['roman']})"

        caption = c.get("caption") or ""

        # For miniature plates, add a seeAlso link to the corpus manuscript
        # register so a viewer / citation tool can jump from a Canvas to the
        # scholarly TEI msDesc entry.
        see_also_entries: list[dict] = []
        ms_xml_id = PLATE_TO_MSDESC.get(c["plate_no"])
        if ms_xml_id:
            see_also_entries.append({
                "id": f"{TEI_BASE.rstrip('/')}/standoff_plates_manuscripts.xml#{ms_xml_id}",
                "type": "Dataset",
                "format": "application/tei+xml",
                "label": {"en": [f"TEI msDesc entry ({ms_xml_id})"]},
                "profile": "https://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng",
            })

        canvas = {
            "id": canvas_id,
            "type": "Canvas",
            "label": {"en": [label_en], "hy": [label_hy]},
            "height": h,
            "width": w,
            "thumbnail": [{
                "id": thumb_url,
                "type": "Image",
                "format": "image/jpeg",
                "width": thumb["width"],
                "height": thumb["height"],
            }],
            "metadata": [
                {
                    "label": {"en": ["Plate number"]},
                    "value": {"none": [f"{c['plate_no']} ({c['roman']})"]},
                },
                {
                    "label": {"en": ["Source page"]},
                    "value": {"none": [f"p. {c['pdf_page']} of the printed volume"]},
                },
                {
                    "label": {"en": ["Caption (as printed)"], "hy": ["Ենթագիր"]},
                    "value": {"hy": [caption] if caption else ["(no caption in text layer)"]},
                },
            ],
            "items": [{
                "id": anno_page_id,
                "type": "AnnotationPage",
                "items": [{
                    "id": anno_id,
                    "type": "Annotation",
                    "motivation": "painting",
                    "body": {
                        "id": f"{image_svc_id}/full/max/0/default.jpg",
                        "type": "Image",
                        "format": "image/jpeg",
                        "width": w,
                        "height": h,
                        "service": [{
                            "id": image_svc_id,
                            "type": "ImageService3",
                            "profile": "level0",
                        }],
                    },
                    "target": canvas_id,
                }],
            }],
        }
        if see_also_entries:
            canvas["seeAlso"] = see_also_entries
        canvases.append(canvas)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = {
        "@context": [
            "http://iiif.io/api/presentation/3/context.json",
        ],
        "id": manifest_id,
        "type": "Manifest",
        "label": {
            "en": ["Babken Chookaszian, Collected Works Vol. I -- Plates insert"],
            "hy": ["Բաբկէն Չուգասզեան, Երկերի ժողովածու Ա հատոր – Լուսանկարներ և մանրանկարներ"],
        },
        "summary": {
            "en": [
                "Photographs and Matenadaran miniatures from the 2nd expanded edition "
                "(Yerevan 2022/2023), pp. 549-571. IIIF v3 level-0 tile hierarchy "
                "generated from the printed PDF; not a facsimile of the original artefacts."
            ]
        },
        "requiredStatement": {
            "label": {"en": ["Attribution"]},
            "value": {"en": [
                "Babken Chookaszian, Collected Works Vol. I (2nd ed., Yerevan 2022/2023). "
                "Digital edition by the Chookaszian estate (© Levon and Garegin "
                "Chugaszyan). Photographs and Matenadaran miniature reproductions used "
                "under pending clearance; NOT for public redistribution."
            ]},
        },
        "rights": "http://rightsstatements.org/vocab/InC-RUW/1.0/",
        "metadata": [
            {"label": {"en": ["Volume"]},
             "value": {"en": ["I (of a projected multi-volume set)"]}},
            {"label": {"en": ["Edition"]},
             "value": {"en": ["Second expanded edition, Yerevan 2022/2023 (impression 2023)"]}},
            {"label": {"en": ["Author"]},
             "value": {"en": ["Babken Chookaszian (Բաբկէն Չուգասզեան, 1923-1997)"]}},
            {"label": {"en": ["Editor / rights holder"]},
             "value": {"en": ["Levon and Garegin Chugaszyan"]}},
            {"label": {"en": ["Insert"]},
             "value": {"en": [
                 f"Plates I-XXIII, pp. 549-571 of the printed volume "
                 f"({len(canvases)} pages: 14 photographic portraits + 9 miniatures)"
             ]}},
            {"label": {"en": ["Public visibility"]},
             "value": {"en": ["pending rights clearance"]}},
            {"label": {"en": ["Rights notice"]},
             "value": {"en": [
                 "Miniatures reproduced from Matenadaran manuscripts require separate "
                 "clearance per each shelfmark. Photographs remain in copyright until "
                 "2067-12-31 (life+70). New descriptive metadata: CC BY 4.0."
             ]}},
            {"label": {"en": ["Generated"]},
             "value": {"en": [f"{now} by iiif/create_manifest.py"]}},
        ],
        "provider": [{
            "id": "https://www.matenadaran.am",
            "type": "Agent",
            "label": {"en": ["Matenadaran (source of miniatures) -- pending clearance"]},
        }],
        # Manifest-level seeAlso points at the TEI standoff register that
        # documents every Matenadaran shelfmark reproduced in the insert.
        "seeAlso": [{
            "id": f"{TEI_BASE.rstrip('/')}/standoff_plates_manuscripts.xml",
            "type": "Dataset",
            "format": "application/tei+xml",
            "label": {"en": ["Matenadaran manuscript register (TEI standoff)"]},
        }],
        "items": canvases,
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pages", default=str(DEFAULT_PAGES))
    p.add_argument("--tiles", default=str(DEFAULT_TILES))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--base", default=DEFAULT_BASE,
                   help="Public base URL where /<plate_id>/... is served")
    p.add_argument("--manifest-id", default=f"{MANIFEST_BASE}/chookaszian-plates",
                   help="Absolute URL that will resolve to this manifest")
    args = p.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(
        pages_dir=Path(args.pages),
        tiles_dir=Path(args.tiles),
        base_url=args.base,
        manifest_id=args.manifest_id,
    )

    out_file = out_dir / "manifest.json"
    out_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote IIIF v3 manifest: {out_file}")
    print(f"  Canvases: {len(manifest['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
