"""Generate minimal TEI XML from extracted article text files."""
from pathlib import Path
from xml.sax.saxutils import escape


def parse_article_payload(raw_text: str):
    lines = raw_text.splitlines()
    title = None
    source_pages = None
    i = 0

    # Optional metadata header emitted by ToC-based splitter.
    while i < len(lines) and lines[i].startswith('# '):
        header = lines[i][2:].strip()
        if title is None:
            title = header
        elif header.lower().startswith('source_pages:'):
            source_pages = header.split(':', 1)[1].strip()
        i += 1

    body_text = '\n'.join(lines[i:]).strip()
    if not title:
        title = body_text[:120].strip() or 'Untitled Article'

    paragraphs = [p.strip() for p in body_text.split('\n\n') if p.strip()]
    if not paragraphs and body_text:
        paragraphs = [body_text]

    return title, source_pages, paragraphs

def articles_to_tei(articles_dir: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    articles_path = Path(articles_dir)
    for i, article_file in enumerate(sorted(articles_path.glob('article_*.txt')), start=1):
        text = article_file.read_text(encoding='utf-8')
        title, source_pages, paragraphs = parse_article_payload(text)
        slug = f"article_{i:03}"
        para_xml = '\n'.join([f"        <p>{escape(p)}</p>" for p in paragraphs])
        source_note = ''
        if source_pages:
            source_note = f'        <note type="source_pages">{escape(source_pages)}</note>\n'
        tei_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="hy">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{escape(title)}</title>
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
        <head>{escape(title)}</head>
{source_note}{para_xml}
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
