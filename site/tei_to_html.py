"""Convert TEI articles to HTML content fragments for the Astro layout.

Output is a *fragment* (semantic markup, no <html>/<head>/<body>), so
`src/pages/articles/[slug].astro` can wrap it in the site's BaseLayout.
The fragment contains:

- <h1> with the article title
- optional <p class="source-pages"> with the printed page range
- the article body: paragraphs plus <a class="pb"> anchor labels
  emitted at every <pb n="P"/> milestone (Phase 2 acceptance)
- an <aside class="entities"> panel listing enriched persons + linked
  Matenadaran manuscripts (uses TEI-P5-correct <listBibl>/<msDesc>
  container introduced in commit 4a4be79). Provenance (@resp) is
  surfaced next to each auto-extracted entity.

Style is intentionally NOT emitted inline; global.css owns it.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'


def _text_or_default(node, default: str = '') -> str:
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _resp_label(resp: str) -> str:
    """Return a human-readable provenance chip for @resp values.

    Convention (CLAUDE.md AI ethics rule): auto-extracted entities carry
    @resp with a token like 'auto:enrich_tei.py'. Reviewed entities have
    the reviewer's key. Blank => unlabelled.
    """
    if not resp:
        return ''
    r = resp.lower()
    if 'auto' in r and 'review' not in r:
        return 'auto (unreviewed)'
    if 'auto' in r:
        return 'auto (reviewed)'
    return resp


def _render_persons(persons: list, out) -> None:
    ul = etree.SubElement(out, 'ul')
    ul.set('class', 'persons')
    for person in persons:
        pn = person.find('tei:persName', NS)
        if pn is None or not (pn.text or '').strip():
            continue
        li = etree.SubElement(ul, 'li')
        ref = pn.get('ref')
        resp = pn.get('resp', '')
        name_el = etree.SubElement(li, 'a') if ref else etree.SubElement(li, 'span')
        name_el.text = pn.text.strip()
        if ref:
            name_el.set('href', ref)
            name_el.set('target', '_blank')
            name_el.set('rel', 'noopener')
        resp_label = _resp_label(resp)
        if resp_label:
            chip = etree.SubElement(li, 'span')
            chip.set('class', 'resp-chip')
            chip.text = resp_label


def _render_msDescs(msDescs: list, out) -> None:
    if not msDescs:
        return
    h4 = etree.SubElement(out, 'h4')
    h4.text = 'Manuscripts'
    ul = etree.SubElement(out, 'ul')
    ul.set('class', 'manuscripts')
    for md in msDescs:
        idno = md.find('.//tei:idno', NS)
        if idno is None or not (idno.text or '').strip():
            continue
        li = etree.SubElement(ul, 'li')
        # Prefer a note/ref (Bodleian URL, Matenadaran catalogue link).
        ref_el = md.find('.//tei:note/tei:ref', NS)
        if ref_el is not None and ref_el.get('target'):
            a = etree.SubElement(li, 'a')
            a.set('href', ref_el.get('target'))
            a.set('target', '_blank')
            a.set('rel', 'noopener')
            a.text = idno.text.strip()
        else:
            li.text = idno.text.strip()


def tei_to_html(tei_path: str, out_path: str) -> None:
    tree = etree.parse(tei_path)

    title_el = tree.find('.//tei:titleStmt/tei:title', NS)
    title = _text_or_default(title_el, 'Untitled article')

    body = tree.find('.//tei:body', NS)
    source_pages_el = tree.find('.//tei:body//tei:note[@type="source_pages"]', NS)
    source_pages = _text_or_default(source_pages_el)

    root = etree.Element('article')
    root.set('class', 'article')
    root.set('lang', 'hy')

    header = etree.SubElement(root, 'header')
    h1 = etree.SubElement(header, 'h1')
    h1.text = title
    if source_pages:
        pmeta = etree.SubElement(header, 'p')
        pmeta.set('class', 'source-pages')
        pmeta.text = f'Printed pages {source_pages}'

    # Body: walk div children in document order so <pb/> and <p> stay
    # interleaved with the correct pagination.
    if body is not None:
        for div in body.findall('tei:div', NS):
            for child in div:
                tag = etree.QName(child).localname
                if tag == 'head':
                    continue  # already used as <h1>
                if tag == 'note' and child.get('type') == 'source_pages':
                    continue  # already promoted to header meta
                if tag == 'pb':
                    n = child.get('n')
                    if not n:
                        continue
                    pb_a = etree.SubElement(root, 'a')
                    pb_a.set('class', 'pb')
                    pb_a.set('id', f'p{n}')
                    pb_a.set('href', f'#p{n}')
                    pb_a.set('aria-label', f'Printed page {n}')
                    pb_a.text = f'p. {n}'
                elif tag == 'p':
                    p_el = etree.SubElement(root, 'p')
                    p_el.text = (child.text or '').strip()
                elif tag == 'note':
                    fn = etree.SubElement(root, 'p')
                    fn.set('class', 'footnote')
                    fn.text = (child.text or '').strip()

    # Entities panel (standOff). TEI P5 uses <listBibl> to wrap
    # <msDesc> — the commit 4a4be79 fix.
    standoff = tree.find('.//tei:standOff', NS)
    if standoff is not None:
        persons = standoff.findall('.//tei:listPerson/tei:person', NS)
        msDescs = standoff.findall('.//tei:listBibl/tei:msDesc', NS)
        if persons or msDescs:
            panel = etree.SubElement(root, 'aside')
            panel.set('class', 'entities')
            ph = etree.SubElement(panel, 'h3')
            ph.text = 'Identified entities'
            note_p = etree.SubElement(panel, 'p')
            note_p.set('class', 'entities-note')
            note_p.text = (
                'Auto-extracted by pipeline/enrich_tei.py. '
                'Unreviewed entries carry a chip; verify against the '
                'article text before citing.'
            )
            if persons:
                _render_persons(persons, panel)
            _render_msDescs(msDescs, panel)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    xml_bytes = etree.tostring(root, pretty_print=True, method='html', encoding='unicode')
    out.write_text(xml_bytes, encoding='utf-8')


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: tei_to_html.py tei.xml out.html')
    else:
        tei_to_html(sys.argv[1], sys.argv[2])
