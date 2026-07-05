"""Split a full-text file into article-level files using a printed ToC.
Placeholder splitter that demonstrates API."""

from pathlib import Path

def split_articles(text_file: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    txt = Path(text_file).read_text()
    # naive split by 'ARTICLE_BREAK' marker (placeholder)
    parts = txt.split('ARTICLE_BREAK')
    for i, part in enumerate(parts, start=1):
        Path(out_dir, f"article_{i:03}.txt").write_text(part)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: split_articles.py input.txt out_dir")
    else:
        split_articles(sys.argv[1], sys.argv[2])
