"""TEI enrichment: NER, entity linking to Wikidata, manuscript reference detection.

Defaults to enriching article_001..article_055 and skips back matter files unless
--include-backmatter is explicitly passed.
"""
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

# Manuscript reference patterns: Մատենադարան/Matenadaran shelfmark
MATENADARAN_PATTERN = r'(?:Մատենադարան|Matenadaran)\s+(?:ձեռ\.|ms\.|MS\.)\s*(\d+)'
FOREIGN_MS_PATTERN = r'(?:British Library|BL|Bodleian|Vatican|BNF|Ms\.|MS\.|fol\.|f\.)[\s\w\d\-\.]*'

def extract_armenian_names(text: str) -> List[str]:
    """Extract likely Armenian person names (simple heuristic)."""
    # Armenian script: U+0530–U+058F
    name_pattern = r'[\u0530-\u058F]+(?:\s+[\u0530-\u058F]+)*'
    names = re.findall(name_pattern, text)
    # Filter: names with 2+ words and reasonable length
    names = [n for n in names if len(n.split()) >= 2 and len(n) > 5]
    return names[:10]  # Limit to top 10

def detect_manuscript_refs(text: str) -> List[Dict]:
    """Detect Matenadaran and foreign manuscript references."""
    refs = []
    # Matenadaran refs
    for match in re.finditer(MATENADARAN_PATTERN, text):
        refs.append({
            'type': 'manuscript_matenadaran',
            'text': match.group(0),
            'shelfmark': match.group(1),
            'url': f'https://www.matenadaran.am/eng/catalog?query={match.group(1)}'
        })
    # Foreign ms refs
    for match in re.finditer(FOREIGN_MS_PATTERN, text):
        refs.append({
            'type': 'manuscript_foreign',
            'text': match.group(0)
        })
    return refs

def enrich_tei_with_standoff(tei_file: str, out_file: str):
    """Add standOff register for entities and manuscripts to TEI."""
    tree = etree.parse(tei_file)
    root = tree.getroot()
    
    # Extract body text
    body = root.find('.//tei:body', NS)
    if body is None:
        return
    
    text_content = etree.tostring(body, encoding='unicode', method='text')
    
    # Extract entities
    names = extract_armenian_names(text_content)
    ms_refs = detect_manuscript_refs(text_content)
    
    # Create standOff element
    standoff = etree.Element('{%s}standOff' % NS['tei'])
    
    # Add person list
    persons = etree.SubElement(standoff, '{%s}listPerson' % NS['tei'])
    for i, name in enumerate(names, start=1):
        person = etree.SubElement(persons, '{%s}person' % NS['tei'], id=f'person_{i}')
        persName = etree.SubElement(person, '{%s}persName' % NS['tei'])
        persName.text = name
        persName.set('{http://www.w3.org/XML/1998/namespace}lang', 'hy')
    
    # Add manuscript refs
    if ms_refs:
        msDescs = etree.SubElement(standoff, '{%s}listMSDesc' % NS['tei'])
        for i, ref in enumerate(ms_refs, start=1):
            msDesc = etree.SubElement(msDescs, '{%s}msDesc' % NS['tei'], id=f'ms_{i}')
            idno = etree.SubElement(msDesc, '{%s}msIdentifier' % NS['tei'])
            shelfmark = etree.SubElement(idno, '{%s}altIdentifier' % NS['tei'])
            idnoVal = etree.SubElement(shelfmark, '{%s}idno' % NS['tei'])
            idnoVal.text = ref.get('shelfmark') or ref['text']
            if ref.get('url'):
                note = etree.SubElement(msDesc, '{%s}note' % NS['tei'])
                ref_elem = etree.SubElement(note, '{%s}ref' % NS['tei'], target=ref['url'])
                ref_elem.text = ref['text']
    
    root.append(standoff)
    
    # Serialize to string with proper encoding
    xml_str = etree.tostring(root, pretty_print=True, encoding='unicode')
    # Prepend XML declaration manually for unicode output
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    Path(out_file).write_text(xml_str, encoding='utf-8')
    print(f'Enriched: {Path(tei_file).name} -> {Path(out_file).name} (found {len(names)} names, {len(ms_refs)} ms refs)')


def _article_number_from_name(file_name: str):
    m = re.fullmatch(r'article_(\d{3})\.xml', file_name)
    if not m:
        return None
    return int(m.group(1))


def batch_enrich(tei_dir: str, out_dir: str, include_backmatter: bool = False, start_article: int = 1, end_article: int = 55):
    """Batch enrich TEI files with standOff.

    By default only enriches article_001..article_055.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    total = 0
    processed = 0
    skipped = 0
    for tei_file in sorted(Path(tei_dir).glob('*.xml')):
        total += 1
        article_num = _article_number_from_name(tei_file.name)
        if article_num is None:
            if not include_backmatter:
                skipped += 1
                print(f'Skipping non-article TEI: {tei_file.name}')
                continue
        elif not include_backmatter and not (start_article <= article_num <= end_article):
            skipped += 1
            print(f'Skipping back matter candidate: {tei_file.name}')
            continue

        out_file = Path(out_dir) / tei_file.name
        try:
            enrich_tei_with_standoff(str(tei_file), str(out_file))
            processed += 1
        except Exception as e:
            print(f'Error enriching {tei_file.name}: {e}')
    print(f'Enrichment summary: processed={processed}, skipped={skipped}, total={total}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enrich TEI files with standOff entities/manuscript refs.')
    parser.add_argument('tei_dir', help='Input TEI directory')
    parser.add_argument('output_dir', help='Output directory for enriched TEI')
    parser.add_argument('--include-backmatter', action='store_true', help='Also enrich files outside article_001..article_055')
    parser.add_argument('--start-article', type=int, default=1, help='First article number to enrich (default: 1)')
    parser.add_argument('--end-article', type=int, default=55, help='Last article number to enrich (default: 55)')
    args = parser.parse_args()
    batch_enrich(
        args.tei_dir,
        args.output_dir,
        include_backmatter=args.include_backmatter,
        start_article=args.start_article,
        end_article=args.end_article,
    )
