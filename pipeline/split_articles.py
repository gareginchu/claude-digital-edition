"""Split a full-text file into article-level files using a printed ToC.
Placeholder splitter that demonstrates API."""

from pathlib import Path

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
