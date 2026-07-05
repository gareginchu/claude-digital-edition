"""Parse printed ToC entries from the extracted text layer.

The volume's printed ToC is on the last two pages (pp. 572-573).
This parser extracts entries in the form: TITLE .... PAGE
"""

import re
from pathlib import Path
from typing import Dict, List


ENTRY_RE = re.compile(r"^(?P<title>.+?)\s*\.{2,}\s*(?P<page>\d{1,3})\s*$")


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _toc_text_block(extracted_text: str) -> str:
    pages = extracted_text.split("\f")
    marker_re = re.compile(r"ԲՈՎԱՆԴԱԿ|CONTENTS|СОДЕРЖ", re.IGNORECASE)
    candidates = [p for p in pages if marker_re.search(p)]
    # Fallback: keep previous behavior if markers are not found.
    if not candidates:
        candidates = pages[-2:] if len(pages) >= 2 else pages
    return "\n".join(candidates)


def parse_toc_entries(extracted_text: str) -> List[Dict[str, int]]:
    toc_text = _toc_text_block(extracted_text)
    entries: List[Dict[str, int]] = []
    seen = set()
    buffer = ""

    for raw_line in toc_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "ԲՈՎԱՆԴԱԿ" in line.upper() or "CONTENTS" in line.upper() or "СОДЕРЖ" in line.upper():
            buffer = ""
            continue
        # Ignore standalone page artifacts from extraction.
        if re.fullmatch(r"\d{1,3}", line):
            continue

        probe = _normalize_spaces(f"{buffer} {line}" if buffer else line)
        m = ENTRY_RE.match(probe)
        if m:
            title = _normalize_spaces(m.group("title")).strip("-– ")
            page = int(m.group("page"))
            # Guardrails: valid page range and unique title-page tuples.
            if 1 <= page <= 573 and (title, page) not in seen:
                entries.append({"title": title, "page": page})
                seen.add((title, page))
            buffer = ""
        else:
            # Keep buffering wrapped lines until a dotted leader + page appears.
            buffer = probe

    # Stable ordering by printed start page.
    entries.sort(key=lambda x: x["page"])
    return entries


def parse_toc(extracted_text: str) -> List[str]:
    """Backward-compatible API returning `title\tpage` lines."""
    return [f"{e['title']}\t{e['page']}" for e in parse_toc_entries(extracted_text)]


if __name__ == "__main__":
    import sys

    t = Path(sys.argv[1]).read_text(encoding="utf-8")
    for l in parse_toc(t):
        print(l)
