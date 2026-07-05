"""Generate minimal TEI XML from extracted article text files."""
from pathlib import Path
from datetime import datetime

def articles_to_tei(articles_dir: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    articles_path = Path(articles_dir)
    for i, article_file in enumerate(sorted(articles_path.glob('article_*.txt')), start=1):
        text = article_file.read_text(encoding='utf-8')
        slug = f"article_{i:03}"
        title = text[:100] if text else f"Article {i}"
        tei_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="hy">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{title}</title>
      </titleStmt>
      <publicationStmt>
        <p>Unpublished draft from Babken Chookaszian volume I extraction</p>
      </publicationStmt>
      <sourceDesc>
        <p>Extracted from Babken_Chookaszian_Vol_I (2).pdf</p>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>Article {i}</head>
        <p>{text[:500]}</p>
        <note>Full text truncated for TEI draft. See {article_file.name} for complete extraction.</note>
      </div>
    </body>
  </text>
</TEI>"""
        out_file = Path(out_dir) / f"{slug}.xml"
        out_file.write_text(tei_xml, encoding='utf-8')
        print(f"Created {out_file}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: generate_tei_drafts.py articles_dir output_dir")
    else:
        articles_to_tei(sys.argv[1], sys.argv[2])
