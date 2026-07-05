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
        "p { margin: 0.75rem 0; white-space: pre-wrap; } "
        "aside.entities { margin-top: 2rem; border-top: 1px solid #ddd; padding-top: 1rem; "
        "font-size: 0.9rem; color: #444; } "
        "aside.entities h3 { font-size: 1rem; margin-bottom: 0.5rem; } "
        "aside.entities h4 { font-size: 0.9rem; margin: 0.75rem 0 0.25rem; } "
        "aside.entities ul { list-style: none; padding: 0; margin: 0; } "
        "aside.entities li { display: inline-block; margin: 0.15rem 0.4rem 0.15rem 0; "
        "background: #f5f5f5; border-radius: 3px; padding: 0.1rem 0.4rem; } "
        "aside.entities a { color: #1a6a9a; text-decoration: none; } "
        "aside.entities a:hover { text-decoration: underline; } "
        ".unreviewed { color: #999; font-size: 0.8em; }"
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

    # Render standOff entity panel if present
    standoff = tree.find('.//tei:standOff', NS)
    if standoff is not None:
        persons = standoff.findall('.//tei:listPerson/tei:person', NS)
        ms_descs = standoff.findall('.//tei:listMSDesc/tei:msDesc', NS)
        if persons or ms_descs:
            panel = etree.SubElement(b, 'aside')
            panel.set('class', 'entities')
            ph = etree.SubElement(panel, 'h3')
            ph.text = 'Identified entities'
            if persons:
                pl = etree.SubElement(panel, 'ul')
                pl.set('class', 'persons')
                for person in persons:
                    pn = person.find('tei:persName', NS)
                    if pn is None or not pn.text:
                        continue
                    li = etree.SubElement(pl, 'li')
                    ref = pn.get('ref')
                    resp = pn.get('resp', '')
                    if ref:
                        a = etree.SubElement(li, 'a')
                        a.set('href', ref)
                        a.set('target', '_blank')
                        a.set('rel', 'noopener')
                        a.text = pn.text.strip()
                        if 'auto' in resp:
                            note = etree.SubElement(li, 'span')
                            note.set('class', 'unreviewed')
                            note.text = ' (auto, unreviewed)'
                    else:
                        li.text = pn.text.strip()
            if ms_descs:
                msl = etree.SubElement(panel, 'ul')
                msl.set('class', 'manuscripts')
                msh = etree.SubElement(panel, 'h4')
                msh.text = 'Manuscripts'
                for msd in ms_descs:
                    idno = msd.find('.//tei:idno', NS)
                    ref_el = msd.find('.//tei:ref', NS)
                    if idno is None or not idno.text:
                        continue
                    li = etree.SubElement(msl, 'li')
                    if ref_el is not None and ref_el.get('target'):
                        a = etree.SubElement(li, 'a')
                        a.set('href', ref_el.get('target'))
                        a.set('target', '_blank')
                        a.set('rel', 'noopener')
                        a.text = idno.text.strip()
                    else:
                        li.text = idno.text.strip()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(etree.tostring(html_root, pretty_print=True, method='html', encoding='unicode'), encoding='utf-8')

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: tei_to_html.py tei.xml out.html')
    else:
        tei_to_html(sys.argv[1], sys.argv[2])
