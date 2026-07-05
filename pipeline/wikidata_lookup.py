"""Wikidata QID lookup for enriched TEI person entities.

Reads tei_enriched/*.xml, queries Wikidata SPARQL for each <persName> that lacks
a @ref attribute, and writes the QID back as @ref="https://www.wikidata.org/wiki/QNNN".

Usage:
    python pipeline/wikidata_lookup.py tei_enriched [--dry-run] [--delay 1.2]

Rate limiting: one SPARQL request per person name, with --delay seconds between
requests (default 1.2 s) to stay well within the Wikidata 50 req/s policy.

AI-assistance note: This script performs automated entity linking. Every match
must be reviewed by a human before the @ref attribute is considered citable.
Each linked persName carries resp="#wikidata_lookup_auto" until reviewed.
"""
import re
import time
import argparse
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}
XML_NS = 'http://www.w3.org/XML/1998/namespace'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'
USER_AGENT = 'ChookaszianDigitalEdition/0.1 (research; contact: chookaszian-edition@example.org)'


def _sparql_query(sparql: str) -> Optional[dict]:
    encoded = quote(sparql)
    url = f'{WIKIDATA_SPARQL}?query={encoded}&format=json'
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/sparql-results+json'})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (URLError, Exception):
        return None


def _canonical_forms(name: str) -> List[str]:
    """Generate candidate canonical (nominative) forms from an inflected Armenian name.

    Wikidata stores nominative Armenian names. Our extractor produces genitive/dative
    inflections. We strip common suffixes and return a priority list to try.
    """
    name = name.strip()
    candidates = [name]
    # Strip common Armenian inflectional suffixes (longest first)
    suffixes = ['ինը', 'ցուն', 'ցու', 'անը', 'անի', 'ային', 'այի', 'ուն', 'ու', 'ին', 'ը', 'ն', 'ի']
    for sfx in suffixes:
        if name.endswith(sfx) and len(name) - len(sfx) >= 4:
            stem = name[:-len(sfx)]
            candidates.append(stem)
            break
    # Also try last-token only (family name)
    tokens = name.split()
    if len(tokens) > 1:
        candidates.append(tokens[-1])
        candidates.append(tokens[0])
    return list(dict.fromkeys(candidates))  # deduplicated, order preserved


def _lookup_armenian_person(name: str) -> Optional[str]:
    """Return a Wikidata QID string (e.g. 'Q12345') for a person name, or None."""
    name_nfc = unicodedata.normalize('NFC', name.strip())
    for candidate in _canonical_forms(name_nfc):
        # Try Armenian label
        sparql = f"""
SELECT ?item WHERE {{
  ?item wdt:P31 wd:Q5 .
  ?item rdfs:label "{candidate}"@hy .
}}
LIMIT 2
"""
        data = _sparql_query(sparql)
        if data is None:
            continue
        results = data.get('results', {}).get('bindings', [])
        if len(results) == 1:
            uri = results[0]['item']['value']
            return uri.rsplit('/', 1)[-1]
    return None


def lookup_and_annotate(tei_enriched_dir: str, dry_run: bool = False, delay: float = 1.2):
    """Walk tei_enriched/, query Wikidata for each unlinked persName, patch @ref."""
    tei_dir = Path(tei_enriched_dir)
    total_queried = 0
    total_linked = 0
    total_ambiguous = 0

    for xml_file in sorted(tei_dir.glob('article_*.xml')):
        tree = etree.parse(str(xml_file))
        root = tree.getroot()
        persons = root.findall('.//tei:standOff/tei:listPerson/tei:person', NS)
        if not persons:
            continue

        changed = False
        for person in persons:
            persName = person.find('tei:persName', NS)
            if persName is None or not persName.text:
                continue
            if persName.get('ref'):
                continue  # already linked

            name = persName.text.strip()
            total_queried += 1
            qid = _lookup_armenian_person(name)
            time.sleep(delay)

            if qid:
                persName.set('ref', f'https://www.wikidata.org/wiki/{qid}')
                persName.set('resp', '#wikidata_lookup_auto')
                print(f'  LINKED  {xml_file.name}: {name!r} -> {qid}')
                total_linked += 1
                changed = True
            else:
                print(f'  NO MATCH {xml_file.name}: {name!r}')
                total_ambiguous += 1

        if changed and not dry_run:
            xml_str = etree.tostring(root, pretty_print=True, encoding='unicode')
            xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
            xml_file.write_text(xml_str, encoding='utf-8')

    print(f'\nSummary: queried={total_queried}, linked={total_linked}, no_match={total_ambiguous}')
    if dry_run:
        print('(dry-run: no files written)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Look up Wikidata QIDs for enriched TEI person entities.')
    parser.add_argument('tei_enriched_dir', help='Directory of enriched TEI files')
    parser.add_argument('--dry-run', action='store_true', help='Query but do not write results')
    parser.add_argument('--delay', type=float, default=1.2, help='Seconds between SPARQL requests (default: 1.2)')
    args = parser.parse_args()
    lookup_and_annotate(args.tei_enriched_dir, dry_run=args.dry_run, delay=args.delay)
