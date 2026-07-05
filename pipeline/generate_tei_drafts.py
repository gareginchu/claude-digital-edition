"""Generate minimal TEI XML from extracted article text files.

Each raw article file (`pipeline/articles/article_NNN.txt`) is transformed
into a TEI P5 draft in `tei/article_NNN.xml`. The extraction preserves
form-feed characters (\\x0c) at each printed-page boundary, so the
generator emits `<pb n="P"/>` milestones inside the body at every
boundary — the Phase 2 acceptance criterion ("every page break present").

Off-by-one mismatches between form-feed count and the metadata
`source_pages` range are logged; the article is still written with as
many `<pb/>` markers as the form-feeds provide.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

PAGE_RANGE_RE = re.compile(r'\s*(\d+)\s*-\s*(\d+)\s*')
SINGLE_PAGE_RE = re.compile(r'\s*(\d+)\s*')
FORM_FEED = '\x0c'


def parse_article_payload(raw_text: str):
    # Do NOT use str.splitlines() here: Python treats \x0c (form-feed) as a
    # line boundary, and we need form-feeds preserved so we can emit <pb/>
    # milestones later. Split on \n only, then slice the original text.
    title = None
    source_pages = None
    header_end = 0
    for line in raw_text.split('\n'):
        if line.startswith('# '):
            header = line[2:].strip()
            if header.lower().startswith('source_pages:'):
                source_pages = header.split(':', 1)[1].strip()
            elif title is None:
                title = header
            header_end += len(line) + 1  # include the '\n'
        else:
            break

    body_text = raw_text[header_end:].strip('\n').strip(FORM_FEED)
    if not title:
        title = body_text[:120].strip() or 'Untitled Article'

    return title, source_pages, body_text


def _page_number_sequence(source_pages: str | None) -> list[int]:
    if not source_pages:
        return []
    m = PAGE_RANGE_RE.fullmatch(source_pages)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    m = SINGLE_PAGE_RE.fullmatch(source_pages)
    if m:
        return [int(m.group(1))]
    return []


def _split_body_by_page(body_text: str) -> list[str]:
    """Split on form-feed. Returns a list where item[i] is the raw text of
    page i (in the article's own page ordering)."""
    return body_text.split(FORM_FEED)


def _render_body(body_text: str, page_numbers: list[int]) -> tuple[str, str | None]:
    """Build the div's inner XML (pb markers + p elements). Returns
    (xml_string, warning_or_None)."""
    page_chunks = _split_body_by_page(body_text)
    warning: str | None = None

    if page_numbers and len(page_chunks) != len(page_numbers):
        warning = (
            f'page chunk / source_pages mismatch: '
            f'{len(page_chunks)} form-feed segments vs {len(page_numbers)} expected pages'
        )

    lines: list[str] = []
    for i, chunk in enumerate(page_chunks):
        # Emit <pb/> at the top of every page whose number we know. Empty
        # trailing chunk (article ending right at a form-feed) is skipped.
        page_no = page_numbers[i] if i < len(page_numbers) else None
        if page_no is not None:
            lines.append(f'        <pb n="{page_no}"/>')
        for para in chunk.split('\n\n'):
            para = para.strip()
            if para:
                lines.append(f'        <p>{escape(para)}</p>')

    return '\n'.join(lines), warning


def articles_to_tei(articles_dir: str, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    articles_path = Path(articles_dir)
    warnings: list[str] = []
    for i, article_file in enumerate(sorted(articles_path.glob('article_*.txt')), start=1):
        text = article_file.read_text(encoding='utf-8')
        title, source_pages, body_text = parse_article_payload(text)
        page_numbers = _page_number_sequence(source_pages)
        body_xml, warn = _render_body(body_text, page_numbers)
        if warn:
            warnings.append(f'{article_file.stem}: {warn}')

        slug = f'article_{i:03}'
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
{source_note}{body_xml}
      </div>
    </body>
  </text>
</TEI>"""
        out_file = Path(out_dir) / f'{slug}.xml'
        out_file.write_text(tei_xml, encoding='utf-8')
        print(f'Created {out_file}')

    if warnings:
        print('\n=== Page-break warnings ===', file=sys.stderr)
        for w in warnings:
            print(f'  ! {w}', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: generate_tei_drafts.py articles_dir output_dir')
    else:
        articles_to_tei(sys.argv[1], sys.argv[2])
