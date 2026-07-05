"""Generate programmatic QA pairs from tei_enriched/ standOff registers.

SynDARin-adapted methodology: extract entities (persons, msDesc refs) from each
article's standOff, template questions around them, add out-of-scope distractors
for abstention testing. Merges with the human-curated seed set.

Usage:
    python rag/eval/generate_qa_pairs.py \
        --tei-dir tei_enriched \
        --seed rag/eval/qa_pairs.json \
        --out rag/eval/qa_pairs.json \
        --target 100
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def extract_entities(tei_path: Path) -> dict:
    """Return {'article_id', 'title', 'persons': [...], 'ms_refs': [...]}."""
    tree = etree.parse(str(tei_path))
    root = tree.getroot()
    title_el = root.find('.//tei:titleStmt/tei:title', NS)
    title = (title_el.text or '').strip() if title_el is not None else ''
    persons = []
    for p in root.findall('.//tei:standOff/tei:listPerson/tei:person', NS):
        name_el = p.find('tei:persName', NS)
        if name_el is not None and name_el.text:
            persons.append(name_el.text.strip())
    ms_refs = []
    for m in root.findall('.//tei:standOff/tei:listBibl/tei:msDesc', NS):
        idno = m.find('.//tei:idno', NS)
        if idno is not None and idno.text:
            ms_refs.append(idno.text.strip())
    return {
        'article_id': tei_path.stem,
        'title': title,
        'persons': persons,
        'ms_refs': ms_refs,
    }


def gen_person_qas(entities_by_article: list[dict]) -> list[dict]:
    """Person-centric templates."""
    out = []
    seen = set()
    for i, ent in enumerate(entities_by_article):
        for j, person in enumerate(ent['persons']):
            # De-duplicate person names across articles: only anchor to the
            # first article we encounter each person in (retrieval should
            # naturally rank the anchor article higher).
            if person in seen:
                continue
            seen.add(person)
            out.append({
                'id': f'qa_gen_person_{len(out)+1:03d}',
                'question': f'Which article in the corpus discusses {person}?',
                'expected_article': ent['article_id'],
                'expected_contains': person,
                'notes': f'Auto-generated from {ent["article_id"]} standOff person_{j+1}',
                'source': 'programmatic-person',
            })
    return out


def gen_ms_qas(entities_by_article: list[dict]) -> list[dict]:
    """Manuscript-ref templates."""
    out = []
    for ent in entities_by_article:
        for shelfmark in ent['ms_refs']:
            out.append({
                'id': f'qa_gen_ms_{len(out)+1:03d}',
                'question': f'Which article references the manuscript at {shelfmark}?',
                'expected_article': ent['article_id'],
                'expected_contains': shelfmark,
                'notes': f'Auto-generated from {ent["article_id"]} msDesc',
                'source': 'programmatic-ms',
            })
    return out


def gen_title_qas(entities_by_article: list[dict], limit: int = 20) -> list[dict]:
    """Article-title lookup: 'What is discussed in [TITLE]?'"""
    out = []
    for ent in entities_by_article[:limit]:
        if not ent['title']:
            continue
        # Trim overly-long titles for question form.
        short = re.sub(r'\s+', ' ', ent['title'])[:80]
        out.append({
            'id': f'qa_gen_title_{len(out)+1:03d}',
            'question': f'What does the article "{short}" cover?',
            'expected_article': ent['article_id'],
            'notes': 'Auto-generated from titleStmt',
            'source': 'programmatic-title',
        })
    return out


# Out-of-scope distractors: topics unlikely to be in the Chookaszian corpus.
# Testing abstention — expected_article is null.
OUT_OF_SCOPE_QAS = [
    'Who won the FIFA World Cup in 2022?',
    'What is the boiling point of mercury in Fahrenheit?',
    'Describe the plot of the film Inception.',
    'What are the main tenets of Zoroastrianism?',
    'Who composed the opera La Bohème?',
    'What is the population of Tokyo?',
    'Explain the theory of relativity.',
    'Which cryptocurrency had the highest market cap in 2024?',
    'What is the currency of Iceland?',
    'Who wrote the novel Ulysses?',
]


def gen_abstention_qas() -> list[dict]:
    out = []
    for i, q in enumerate(OUT_OF_SCOPE_QAS, start=1):
        out.append({
            'id': f'qa_gen_abstain_{i:03d}',
            'question': q,
            'expected_article': None,
            'notes': 'Out-of-scope; tests abstention',
            'source': 'programmatic-abstention',
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tei-dir', default='tei_enriched')
    parser.add_argument('--seed', default='rag/eval/qa_pairs.json',
                        help='Existing curated QA pairs (kept as-is)')
    parser.add_argument('--out', default='rag/eval/qa_pairs.json')
    parser.add_argument('--target', type=int, default=100,
                        help='Approx target size after merge (soft ceiling)')
    args = parser.parse_args()

    tei_dir = Path(args.tei_dir)
    xml_files = sorted(tei_dir.glob('article_*.xml'))
    entities_by_article = [extract_entities(f) for f in xml_files]

    curated = json.loads(Path(args.seed).read_text(encoding='utf-8')) if Path(args.seed).exists() else []
    curated_by_id = {q['id']: q for q in curated}
    # Mark curated as human-authored if not already tagged.
    for q in curated:
        q.setdefault('source', 'curated')

    person_qas = gen_person_qas(entities_by_article)
    ms_qas = gen_ms_qas(entities_by_article)
    title_qas = gen_title_qas(entities_by_article, limit=20)
    abstention_qas = gen_abstention_qas()

    # Interleave programmatic sources so a small --target still yields all
    # categories (person QAs alone can starve titles + abstention pairs).
    def interleave(*lists: list[dict]) -> list[dict]:
        out: list[dict] = []
        iters = [iter(lst) for lst in lists]
        while iters:
            for i in list(range(len(iters))):
                try:
                    out.append(next(iters[i]))
                except StopIteration:
                    iters[i] = None
            iters = [it for it in iters if it is not None]
        return out

    programmatic = interleave(person_qas, ms_qas, title_qas, abstention_qas)

    # Combine: preserve every curated item, then take as many programmatic as
    # needed to reach the target.
    combined = list(curated)
    combined_ids = {q['id'] for q in combined}
    for q in programmatic:
        if q['id'] in combined_ids:
            continue
        combined.append(q)
        combined_ids.add(q['id'])
        if len(combined) >= args.target:
            break

    Path(args.out).write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    # Summary
    by_source: dict[str, int] = {}
    for q in combined:
        by_source[q.get('source', 'unknown')] = by_source.get(q.get('source', 'unknown'), 0) + 1
    print(f'Wrote {len(combined)} QA pairs to {args.out}')
    print(f'Composition: {by_source}')
    print(f'Programmatic candidates generated (before cap): '
          f'person={len(person_qas)}, ms={len(ms_qas)}, title={len(title_qas)}, '
          f'abstain={len(abstention_qas)}')


if __name__ == '__main__':
    main()
