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
    if title is not None and title.text:
        t = etree.SubElement(head, 'title')
        t.text = title.text
    b = etree.SubElement(html_root, 'body')
    if body is not None:
        for div in body.findall('.//tei:div', NS):
            h = etree.SubElement(b, 'h2')
            head_el = div.find('tei:head', NS)
            if head_el is not None and head_el.text:
                h.text = head_el.text
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
