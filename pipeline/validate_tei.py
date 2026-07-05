"""Validate every TEI XML file in the corpus against TEI P5 RelaxNG (tei_all.rng).

Usage:
    python pipeline/validate_tei.py [--fetch] [DIR ...]

If no DIRs given, validates tei/ and tei_enriched/ by default.
Pass --fetch to (re)download the schema if odd/schemas/tei_all.rng is missing.
Exits non-zero if any file fails validation.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from lxml import etree

SCHEMA_URL = "https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"
SCHEMA_PATH = Path("odd/schemas/tei_all.rng")
DEFAULT_DIRS = ["tei", "tei_enriched"]


def ensure_schema(fetch: bool) -> Path:
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH
    if not fetch:
        sys.stderr.write(
            f"error: schema not found at {SCHEMA_PATH}; rerun with --fetch to download\n"
        )
        sys.exit(2)
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"fetching {SCHEMA_URL} -> {SCHEMA_PATH}\n")
    urllib.request.urlretrieve(SCHEMA_URL, SCHEMA_PATH)
    return SCHEMA_PATH


def load_validator(schema_path: Path) -> etree.RelaxNG:
    with schema_path.open("rb") as f:
        schema_doc = etree.parse(f)
    return etree.RelaxNG(schema_doc)


def validate_file(validator: etree.RelaxNG, xml_path: Path) -> list[str]:
    try:
        doc = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as e:
        return [f"XML parse error: {e}"]
    if validator.validate(doc):
        return []
    return [f"line {e.line}: {e.message}" for e in validator.error_log]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dirs", nargs="*", default=DEFAULT_DIRS,
                        help="Directories to walk for *.xml files")
    parser.add_argument("--fetch", action="store_true",
                        help="Download schema if missing")
    parser.add_argument("--max-errors-per-file", type=int, default=5,
                        help="Truncate error output per file (default: 5)")
    args = parser.parse_args()

    schema_path = ensure_schema(args.fetch)
    validator = load_validator(schema_path)

    xml_files: list[Path] = []
    for d in args.dirs:
        root = Path(d)
        if not root.exists():
            sys.stderr.write(f"warning: {d} does not exist, skipping\n")
            continue
        xml_files.extend(sorted(root.glob("*.xml")))

    if not xml_files:
        sys.stderr.write("error: no XML files found\n")
        return 2

    passed = 0
    failed: list[tuple[Path, list[str]]] = []
    for xml_path in xml_files:
        errors = validate_file(validator, xml_path)
        if errors:
            failed.append((xml_path, errors))
        else:
            passed += 1

    print(f"\n=== TEI validation summary ===")
    print(f"schema:  {schema_path}")
    print(f"scanned: {len(xml_files)} files across {len(args.dirs)} dir(s)")
    print(f"passed:  {passed}")
    print(f"failed:  {len(failed)}")

    if failed:
        print(f"\n=== Failures ===")
        for xml_path, errors in failed:
            print(f"\n{xml_path}")
            for e in errors[: args.max_errors_per_file]:
                print(f"  - {e}")
            if len(errors) > args.max_errors_per_file:
                print(f"  ... {len(errors) - args.max_errors_per_file} more errors")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
