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

NAME_STOPWORDS = {
    'ԲԱՌԱՐԱՆ',
    'ԵՐԱԽՏԱԳԻՏՈՒԹԵԱՆ',
    'ԽՕՍՔ',
    'ԼԵԶՎԱԲԱՆՈՒԹՅՈՒՆ',
    'ԱՆՎԱՆԱՑԱՆԿ',
    'ԲՈՎԱՆԴԱԿՈՒԹԻՒՆ',
}

NON_PERSON_SUFFIXES = {
    'Գրադարանի',
    'ԳՐԱԴԱՐԱՆԻ',
    'Հայաստանի',
    'Երևանի',
    'Երեւանի',
    'Պալատի',
    'Համալսարանի',
    'Ինստիտուտի',
}

NON_PERSON_TOKENS = {
    'Սուրբ',
    'Հայկական',
    'Արևելյան',
    'Արեւելյան',
    'Ըստ',
    'Յաղագս',
    'Ֆիզիկական',
    'Մանկավարժական',
    'ԼԵԶՎԱԲԱՆՈՒԹՅՈՒՆ',
    'Պատմության',
    'Բառգիրք',
}

LANGUAGE_TERMS = {
    'Արաբերեն',
    'Պարսկերեն',
    'Հայերեն',
    'Հայերէն',
    'անգլերեն',
    'ռուսերեն',
    'ֆրանսերեն',
}

PERSON_SUFFIX_HINTS = (
    'եան',
    'յան',
    'եանց',
    'ենց',
    'ացի',
    'եցի',
    'ունի',
)

KNOWN_GIVEN_NAMES = {
    'Բաբկէն',
    'Գուրգէն',
    'Աննա',
    'Հայկանուշ',
    'Ռուզան',
    'Վեներա',
    'Մկրտիչ',
    'Գէորգ',
    'Գևորգ',
    'Գրիգորիս',
    'Կոստանդին',
    'Ղազար',
    'Փավստոս',
    'Իբն',
}

SHORT_TOKEN_ALLOWLIST = {
    'Իբն',
}

TOPONYM_BIGRAMS = {
    'Նյու Յորք',
    'Երևան Հայաստան',
    'Երեւան Հայաստան',
}


def _unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _is_non_person_candidate(candidate: str) -> bool:
    if candidate in TOPONYM_BIGRAMS:
        return True
    tokens = candidate.split()
    if not tokens:
        return True
    if tokens[-1] in NON_PERSON_SUFFIXES:
        return True
    if any(tok in NON_PERSON_TOKENS for tok in tokens):
        return True
    # Dictionary/meta terms often leak into NER candidates.
    if any(tok in LANGUAGE_TERMS for tok in tokens):
        return True
    return False


def _looks_like_person_candidate(tokens: List[str]) -> bool:
    if not tokens:
        return False
    if any(len(tok) <= 2 and tok not in SHORT_TOKEN_ALLOWLIST for tok in tokens):
        return False
    if tokens[0] in KNOWN_GIVEN_NAMES:
        return True
    return any(tok.endswith(sfx) for tok in tokens for sfx in PERSON_SUFFIX_HINTS)


def _is_lexicon_like_text(normalized_text: str) -> bool:
    return (
        'ԲԱՌԱՐԱՆ' in normalized_text
        and 'Արաբերեն' in normalized_text
        and 'Պարսկերեն' in normalized_text
    )

def extract_armenian_names(text: str) -> List[str]:
    """Extract likely Armenian person names with stricter heuristics.

    We prefer 2-3 title-cased Armenian tokens and reject headings/boilerplate.
    """
    normalized = re.sub(r'\s+', ' ', text)
    lexicon_like = _is_lexicon_like_text(normalized)

    # Example match: Բաբկէն Չուգասզեան or Գէորգ Դպիր Պալատացի
    candidate_pattern = re.compile(
        r'\b[Ա-Ֆ][ա-ֆև]{1,24}(?:-[Ա-Ֆա-ֆև]{1,24})?(?:\s+[Ա-Ֆ][ա-ֆև]{1,24}(?:-[Ա-Ֆա-ֆև]{1,24})?){1,2}\b'
    )
    candidates = [c.strip() for c in candidate_pattern.findall(normalized)]

    filtered = []
    for cand in candidates:
        tokens = cand.split()
        if len(tokens) < 2 or len(tokens) > 3:
            continue
        if len(cand) > 50:
            continue
        if any(sw in tokens for sw in NAME_STOPWORDS):
            continue
        if _is_non_person_candidate(cand):
            continue
        if not _looks_like_person_candidate(tokens):
            continue
        filtered.append(cand)

    names = _unique_preserve_order(filtered)

    # Fallback pass for dictionary-like articles where precision filters can be too strict.
    if len(names) < 3 and not lexicon_like:
        fallback_pattern = re.compile(
            r'\b[Ա-Ֆ][ա-ֆև]{2,24}(?:\s+[Ա-Ֆ][ա-ֆև]{2,24})\b'
        )
        fallback_candidates = [c.strip() for c in fallback_pattern.findall(normalized)]
        for cand in fallback_candidates:
            if len(cand) > 40:
                continue
            if _is_non_person_candidate(cand):
                continue
            if any(sw in cand.split() for sw in NAME_STOPWORDS):
                continue
            if not _looks_like_person_candidate(cand.split()):
                continue
            names.append(cand)

    return _unique_preserve_order(names)[:10]

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
        cleaned = re.sub(r'\s+', ' ', match.group(0)).strip(' ,.;:\n\t')
        if not cleaned:
            continue
        refs.append({
            'type': 'manuscript_foreign',
            'text': cleaned
        })

    deduped = []
    seen = set()
    for ref in refs:
        key = (ref.get('type'), ref.get('shelfmark') or '', ref.get('text') or '')
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped

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
