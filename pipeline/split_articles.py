"""Split extracted text into article files using printed ToC page anchors."""

from pathlib import Path


def _read_toc_start_pages(toc_file: str):
    starts = []
    titles = []
    for line in Path(toc_file).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            title, page_s = line.rsplit("\t", 1)
        else:
            # Backward compatibility with older dotted format.
            parts = line.strip().rsplit(" ", 1)
            if len(parts) != 2:
                continue
            title, page_s = parts
        try:
            page = int(page_s)
        except ValueError:
            continue
        starts.append(page)
        titles.append(title.strip())
    return titles, starts


def split_articles_by_toc(text_file: str, toc_file: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    txt = Path(text_file).read_text(encoding="utf-8")
    pages = txt.split("\f")
    total_pages = len(pages)
    if pages and not pages[-1].strip():
        total_pages -= 1
    titles, starts = _read_toc_start_pages(toc_file)

    if not starts:
        raise ValueError("No valid ToC start pages found.")

    # Keep only ascending unique start pages in valid bounds.
    filtered_titles = []
    filtered_starts = []
    prev = 0
    for title, s in zip(titles, starts):
        if s <= prev or s < 1 or s > total_pages:
            continue
        filtered_titles.append(title)
        filtered_starts.append(s)
        prev = s

    for i, start_page in enumerate(filtered_starts):
        end_page = filtered_starts[i + 1] - 1 if i + 1 < len(filtered_starts) else total_pages
        page_slice = pages[start_page - 1 : end_page]
        body = "\n\f\n".join(p.strip() for p in page_slice if p.strip())
        payload = f"# {filtered_titles[i]}\n# source_pages: {start_page}-{end_page}\n\n{body}".strip()
        Path(out_dir, f"article_{i + 1:03}.txt").write_text(payload, encoding="utf-8")


def split_articles(text_file: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    txt = Path(text_file).read_text(encoding='utf-8')
    # Primary: split by explicit marker if present
    if 'ARTICLE_BREAK' in txt:
        parts = txt.split('ARTICLE_BREAK')
    # Secondary: split by page form-feed characters produced by pdf extraction
    elif '\f' in txt:
        parts = [p.strip() for p in txt.split('\f') if p.strip()]
    # Fallback: split into paragraph-based chunks of roughly equal size
    else:
        paragraphs = [p for p in txt.split('\n\n') if p.strip()]
        parts = []
        cur = []
        for p in paragraphs:
            cur.append(p)
            if len('\n\n'.join(cur)) > 5000:
                parts.append('\n\n'.join(cur))
                cur = []
        if cur:
            parts.append('\n\n'.join(cur))
    for i, part in enumerate(parts, start=1):
        Path(out_dir, f"article_{i:03}.txt").write_text(part, encoding='utf-8')

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: split_articles.py input.txt out_dir")
    else:
        split_articles(sys.argv[1], sys.argv[2])
