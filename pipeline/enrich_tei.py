"""TEI enrichment: NER, entity linking to Wikidata, manuscript reference detection."""
import re
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

def batch_enrich(tei_dir: str, out_dir: str):
    """Batch enrich all TEI files with standOff."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for tei_file in sorted(Path(tei_dir).glob('*.xml')):
        out_file = Path(out_dir) / tei_file.name
        try:
            enrich_tei_with_standoff(str(tei_file), str(out_file))
        except Exception as e:
            print(f'Error enriching {tei_file.name}: {e}')

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: enrich_tei.py tei_dir output_dir')
    else:
        batch_enrich(sys.argv[1], sys.argv[2])
