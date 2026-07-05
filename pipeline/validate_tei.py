"""Validate every TEI XML file in the corpus.

Two validation layers are applied to each file:

  1. RelaxNG against TEI P5 tei_all.rng (odd/schemas/tei_all.rng).
  2. ISO Schematron against odd/chookaszian.sch, which encodes the
     project-specific rules documented in odd/chookaszian.odd
     (teiHeader completeness, standOff xml:id requirement, pb/@n,
     xml:lang / @type controlled vocabularies).

Schematron rules with role="warning" are reported but do not fail
validation. Rules with role="error" (and any RelaxNG failure) cause
a non-zero exit.

Usage:
    python pipeline/validate_tei.py [--fetch] [DIR ...]

If no DIRs given, validates tei/ and tei_enriched/ by default.
Pass --fetch to (re)download tei_all.rng if it is missing.
Exits non-zero if any file fails either layer.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from lxml import etree
from lxml import isoschematron

SCHEMA_URL = "https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"
SCHEMA_PATH = Path("odd/schemas/tei_all.rng")
SCHEMATRON_PATH = Path("odd/chookaszian.sch")
DEFAULT_DIRS = ["tei", "tei_enriched"]

SVRL_NS = "{http://purl.oclc.org/dsdl/svrl}"


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


def load_rng_validator(schema_path: Path) -> etree.RelaxNG:
    with schema_path.open("rb") as f:
        schema_doc = etree.parse(f)
    return etree.RelaxNG(schema_doc)


def load_schematron_validator(sch_path: Path) -> Optional[isoschematron.Schematron]:
    if not sch_path.exists():
        sys.stderr.write(
            f"warning: Schematron file not found at {sch_path}; "
            f"skipping project-specific checks\n"
        )
        return None
    with sch_path.open("rb") as f:
        sch_doc = etree.parse(f)
    # store_report=True so we can walk the SVRL result and split
    # errors (role="error" / unset) from warnings (role="warning").
    return isoschematron.Schematron(sch_doc, store_report=True)


def validate_rng(validator: etree.RelaxNG, doc: etree._ElementTree) -> list[str]:
    if validator.validate(doc):
        return []
    return [f"RNG line {e.line}: {e.message}" for e in validator.error_log]


def _svrl_message(failure: etree._Element) -> str:
    text = "".join(failure.itertext()).strip()
    return " ".join(text.split())


def validate_schematron(
    validator: Optional[isoschematron.Schematron],
    doc: etree._ElementTree,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) from Schematron.

    role="warning" -> warnings; anything else (role="error", missing,
    role="fatal") -> errors.
    """
    if validator is None:
        return [], []
    validator.validate(doc)
    report = validator.validation_report
    errors: list[str] = []
    warnings: list[str] = []
    if report is None:
        return errors, warnings
    for failure in report.iter(f"{SVRL_NS}failed-assert",
                               f"{SVRL_NS}successful-report"):
        role = (failure.get("role") or "error").lower()
        rule_id = failure.get("id") or ""
        location = failure.get("location") or ""
        message = _svrl_message(failure)
        line = (
            f"SCH [{rule_id}] {message}"
            if not location
            else f"SCH [{rule_id}] {message} (at {location})"
        )
        if role in ("warning", "info"):
            warnings.append(line)
        else:
            errors.append(line)
    return errors, warnings


def validate_file(
    rng_validator: etree.RelaxNG,
    sch_validator: Optional[isoschematron.Schematron],
    xml_path: Path,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single file."""
    try:
        doc = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as e:
        return [f"XML parse error: {e}"], []

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(validate_rng(rng_validator, doc))
    sch_errors, sch_warnings = validate_schematron(sch_validator, doc)
    errors.extend(sch_errors)
    warnings.extend(sch_warnings)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dirs", nargs="*", default=DEFAULT_DIRS,
                        help="Directories to walk for *.xml files")
    parser.add_argument("--fetch", action="store_true",
                        help="Download RelaxNG schema if missing")
    parser.add_argument("--max-errors-per-file", type=int, default=5,
                        help="Truncate error output per file (default: 5)")
    parser.add_argument("--max-warnings-per-file", type=int, default=5,
                        help="Truncate warning output per file (default: 5)")
    parser.add_argument("--no-schematron", action="store_true",
                        help="Skip the project-specific Schematron layer")
    args = parser.parse_args()

    schema_path = ensure_schema(args.fetch)
    rng_validator = load_rng_validator(schema_path)

    sch_validator = None
    if not args.no_schematron:
        sch_validator = load_schematron_validator(SCHEMATRON_PATH)

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
    warned: list[tuple[Path, list[str]]] = []
    total_warnings = 0
    for xml_path in xml_files:
        errors, warnings = validate_file(rng_validator, sch_validator, xml_path)
        if warnings:
            warned.append((xml_path, warnings))
            total_warnings += len(warnings)
        if errors:
            failed.append((xml_path, errors))
        else:
            passed += 1

    print(f"\n=== TEI validation summary ===")
    print(f"RelaxNG:    {schema_path}")
    print(f"Schematron: {SCHEMATRON_PATH if sch_validator else '(disabled)'}")
    print(f"scanned:    {len(xml_files)} files across {len(args.dirs)} dir(s)")
    print(f"passed:     {passed}")
    print(f"failed:     {len(failed)}")
    print(f"warnings:   {total_warnings} across {len(warned)} file(s)")

    if warned:
        print(f"\n=== Warnings ===")
        for xml_path, warnings in warned:
            print(f"\n{xml_path}")
            for w in warnings[: args.max_warnings_per_file]:
                print(f"  ! {w}")
            if len(warnings) > args.max_warnings_per_file:
                print(f"  ... {len(warnings) - args.max_warnings_per_file} more warnings")

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
