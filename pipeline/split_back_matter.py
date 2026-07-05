"""Split article_056 back matter into structural units (index, plates, contents).

This utility keeps article IDs stable while creating dedicated back-matter files
that can be excluded from article-style enrichment pipelines.
"""

from pathlib import Path


def parse_article_payload(raw_text: str):
    title = ""
    source_pages = ""
    body_text = raw_text

    if raw_text.startswith("# "):
        lines = raw_text.splitlines()
        if lines:
            title = lines[0][2:].strip()
        if len(lines) > 1 and lines[1].startswith("# source_pages:"):
            source_pages = lines[1].split(":", 1)[1].strip()
        marker = "\n\n"
        if marker in raw_text:
            body_text = raw_text.split(marker, 1)[1].strip()

    return title, source_pages, body_text


def parse_page_range(source_pages: str):
    if not source_pages or "-" not in source_pages:
        return None, None
    start, end = source_pages.split("-", 1)
    try:
        return int(start.strip()), int(end.strip())
    except ValueError:
        return None, None


def split_back_matter(article_file: str, out_dir: str):
    raw = Path(article_file).read_text(encoding="utf-8")
    title, source_pages, body = parse_article_payload(raw)
    start_page, _ = parse_page_range(source_pages)

    units = {
        "index": {"title": "ԱՆՎԱՆԱՑԱՆԿ", "pages": [], "texts": []},
        "plates": {"title": "ԼՈՒՍԱՆԿԱՐՆԵՐ ԵՒ ՄԱՆՐԱՆԿԱՐՆԵՐ", "pages": [], "texts": []},
        "contents": {"title": "ԲՈՎԱՆԴԱԿՈՒԹԻՒՆ", "pages": [], "texts": []},
    }

    current = "index"
    for line in body.splitlines():
        if "ԲՈՎԱՆԴԱԿ" in line:
            current = "contents"
        elif "ԼՈՒՍԱՆԿԱՐՆԵՐ ԵՒ ՄԱՆՐԱՆԿԱՐՆԵՐ" in line and current != "contents":
            current = "plates"
        units[current]["texts"].append(line)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for key, meta in units.items():
        if not meta["texts"]:
            continue
        if meta["pages"]:
            source = f"{min(meta['pages'])}-{max(meta['pages'])}"
        elif source_pages:
            source = f"{source_pages} (subset)"
        else:
            source = "unknown"

        payload = (
            f"# {meta['title']}\n"
            f"# source_pages: {source}\n"
            f"# source_unit: {key}\n\n"
            + "\n".join(meta["texts"]).strip()
        )
        out_file = out_path / f"backmatter_{key}.txt"
        out_file.write_text(payload, encoding="utf-8")
        print(f"Created {out_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: split_back_matter.py <article_056.txt> <out_dir>")
    else:
        split_back_matter(sys.argv[1], sys.argv[2])
