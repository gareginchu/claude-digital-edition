"""Convert simple TEI documents to minimal HTML pages for the static site.
Uses lxml to parse and produce readable HTML; this is a lightweight renderer for previews.
"""
from lxml import etree
from pathlib import Path

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def tei_to_html(tei_path: str, out_path: str):
    tree = etree.parse(tei_path)
    title = tree.find('.//tei:title', NS)
    body = tree.find('.//tei:body', NS)
    html_root = etree.Element('html')
    head = etree.SubElement(html_root, 'head')
    meta = etree.SubElement(head, 'meta', charset='utf-8')
    if title is not None and title.text:
        t = etree.SubElement(head, 'title')
        t.text = title.text
    style = etree.SubElement(head, 'style')
    style.text = (
        "body { max-width: 900px; margin: 2rem auto; padding: 0 1rem; "
        "font-family: 'Noto Serif Armenian', serif; line-height: 1.6; } "
        "h1 { font-size: 1.8rem; margin-bottom: 0.25rem; } "
        "h2 { font-size: 1.2rem; margin-top: 0; color: #555; } "
        ".meta { color: #666; font-size: 0.95rem; margin-bottom: 1.25rem; } "
        "p { margin: 0.75rem 0; white-space: pre-wrap; }"
    )
    b = etree.SubElement(html_root, 'body')
    main_title = etree.SubElement(b, 'h1')
    main_title.text = title.text.strip() if title is not None and title.text else 'Article'
    if body is not None:
        for div in body.findall('.//tei:div', NS):
            h = etree.SubElement(b, 'h2')
            head_el = div.find('tei:head', NS)
            if head_el is not None and head_el.text:
                h.text = head_el.text
            source_note = div.find('tei:note[@type="source_pages"]', NS)
            if source_note is not None and source_note.text:
                meta_line = etree.SubElement(b, 'p')
                meta_line.set('class', 'meta')
                meta_line.text = f"Source pages: {source_note.text}"
            for p in div.findall('.//tei:p', NS):
                p_el = etree.SubElement(b, 'p')
                p_el.text = p.text
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(etree.tostring(html_root, pretty_print=True, method='html', encoding='unicode'), encoding='utf-8')

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: tei_to_html.py tei.xml out.html')
    else:
        tei_to_html(sys.argv[1], sys.argv[2])
