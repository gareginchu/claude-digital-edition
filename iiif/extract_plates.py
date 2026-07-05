"""Extract the plates-insert pages from the source PDF as JPEG images.

The Babken Chookaszian Vol. I PDF (2nd ed., Yerevan 2022/2023) contains the
plates insert at pp. 549-571 (Roman numerals I-XXIII), immediately after the
name index (ANVANATSANK) and before the table of contents. This spans 23
printed plate pages: 14 photographic portraits and 9 Matenadaran miniatures
(the CLAUDE.md report refers to it as a "24-pp. insert"; the actual printed
plates run 23 numbered pages -- the difference is presumably a blank verso).

Output: iiif/pages/plate_NN.jpg  (2-digit zero-padded, NN starts at 01)

Also writes iiif/pages/captions.json holding per-plate caption text scraped
from the PDF text layer for use in downstream tile / manifest generation.

Usage:
    python iiif/extract_plates.py                # default paths, all plates
    python iiif/extract_plates.py --dpi 200
    python iiif/extract_plates.py --pdf path/to.pdf --out iiif/pages
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as e:  # pragma: no cover
    print("ERROR: PyMuPDF (pymupdf) not installed. See iiif/README.md.", file=sys.stderr)
    raise

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPO_ROOT / "Babken_Chookaszian_Vol_I (2).pdf"
DEFAULT_OUT = REPO_ROOT / "iiif" / "pages"

# Range of PDF pages (1-indexed) that make up the plates insert.
PLATE_PAGE_START = 549
PLATE_PAGE_END = 571  # inclusive


def _clean_caption(raw: str) -> str:
    """Collapse whitespace and strip the running header from a plate page."""
    text = raw or ""
    # Remove the running header (ARM: LUSANKARNER YEW MANRANKARNER) and the
    # roman-numeral folio marker which appears on every plate page.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    filtered: list[str] = []
    for ln in lines:
        # Skip the running header line.
        if ln.startswith("ԼՈՒՍԱՆԿԱՐՆԵՐ"):
            continue
        # Skip a bare roman-numeral folio marker (I, II, ..., XXIII), possibly
        # followed by nothing else.
        if re.fullmatch(r"[IVX]{1,6}", ln):
            continue
        # Skip a bare ManrANKARNER section header on the first miniature page.
        if ln == "ՄԱՆՐԱՆԿԱՐՆԵՐ":
            continue
        filtered.append(ln)
    caption = " ".join(filtered)
    caption = re.sub(r"\s+", " ", caption).strip()
    return caption


def extract_plate_pages(
    pdf_path: Path,
    out_dir: Path,
    dpi: int = 200,
    start: int = PLATE_PAGE_START,
    end: int = PLATE_PAGE_END,
) -> list[dict]:
    """Render each plate page as a single JPEG at the requested DPI.

    Returns a list of dicts describing each rendered plate:
        {"plate_no": int, "pdf_page": int, "roman": str,
         "file": Path, "width": int, "height": int, "caption": str}
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)

    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    results: list[dict] = []

    for i, pdf_page in enumerate(range(start, end + 1), start=1):
        page = doc[pdf_page - 1]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        # Encode to JPEG via PIL for consistent quality control.
        from PIL import Image  # local import so extract can be imported cheaply

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out_file = out_dir / f"plate_{i:02d}.jpg"
        img.save(out_file, format="JPEG", quality=90, optimize=True)

        raw_text = page.get_text() or ""
        # Roman numeral is on line 2 of every plate page (line 1 is the running
        # header). Fall back to computed roman.
        roman_match = re.search(r"\b([IVX]{1,6})\b", raw_text.splitlines()[1]) \
            if len(raw_text.splitlines()) > 1 else None
        roman = roman_match.group(1) if roman_match else _to_roman(i)

        caption = _clean_caption(raw_text)

        results.append({
            "plate_no": i,
            "pdf_page": pdf_page,
            "roman": roman,
            "file": str(out_file.relative_to(REPO_ROOT).as_posix()),
            "width": pix.width,
            "height": pix.height,
            "caption": caption,
        })

    doc.close()
    return results


def _to_roman(n: int) -> str:
    romans = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = []
    for v, s in romans:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    # Ensure UTF-8 stdout on Windows consoles for the Armenian captions.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", default=str(DEFAULT_PDF), help="Path to source PDF")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    p.add_argument("--dpi", type=int, default=200, help="Render DPI (default 200)")
    p.add_argument("--start", type=int, default=PLATE_PAGE_START,
                   help="First PDF page (1-indexed)")
    p.add_argument("--end", type=int, default=PLATE_PAGE_END,
                   help="Last PDF page (1-indexed, inclusive)")
    args = p.parse_args(argv)

    pdf_path = Path(args.pdf)
    out_dir = Path(args.out)

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    print(f"Extracting plates {args.start}-{args.end} from {pdf_path.name} at {args.dpi} DPI ...")
    results = extract_plate_pages(pdf_path, out_dir, dpi=args.dpi,
                                  start=args.start, end=args.end)

    manifest_out = out_dir / "captions.json"
    manifest_out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Extracted {len(results)} plate pages -> {out_dir}")
    print(f"Wrote caption index -> {manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
