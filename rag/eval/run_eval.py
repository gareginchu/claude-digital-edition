"""Eval harness for the Chookaszian corpus RAG pipeline.

Runs a set of QA pairs against the retrieval index and the /ask API endpoint,
computing:
  - Retrieval recall@k: does the correct article appear in top-k results?
  - Answer citation accuracy: does the answer cite the correct source?
  - Abstention rate: how often does the model correctly say "I don't know"?

Retrieval eval supports a ``--mode`` flag: ``bm25`` (default, unchanged
baseline over ``rag/inverted_index.json``), ``dense`` (BGE-M3 via ChromaDB)
and ``hybrid`` (RRF fusion). ``--mode compare`` runs BM25 and hybrid on the
same QA pairs and prints a side-by-side per-source breakdown.

Usage::

    # BM25 baseline (unchanged behaviour)
    python rag/eval/run_eval.py rag/eval/qa_pairs.json rag/inverted_index.json

    # Hybrid only
    python rag/eval/run_eval.py rag/eval/qa_pairs.json rag/inverted_index.json \
        --mode hybrid

    # Side-by-side BM25 vs hybrid
    python rag/eval/run_eval.py rag/eval/qa_pairs.json rag/inverted_index.json \
        --mode compare

    # /ask API eval (unchanged)
    python rag/eval/run_eval.py --api http://localhost:5000 rag/eval/qa_pairs.json
"""
import io
import json
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Force UTF-8 stdout on Windows so Armenian characters in miss reports do not
# crash the eval mid-print (cp1252 default cannot encode U+0530-U+058F).
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def _load_index(index_path: str):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.indexer import CorpusIndex
    return CorpusIndex.load(index_path)


def _bm25_searcher(index):
    def _search(query: str, top_k: int) -> List[Dict]:
        return index.search(query, top_k=top_k)
    return _search


def _hybrid_searcher(mode: str):
    """Return a search function for ``dense`` or ``hybrid`` mode."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.hybrid_retrieve import hybrid_search

    def _search(query: str, top_k: int) -> List[Dict]:
        return hybrid_search(query, top_k=top_k, mode=mode)
    return _search


def _retrieval_eval(
    qa_pairs: List[Dict],
    search_fn: Callable[[str, int], List[Dict]],
    top_k: int = 5,
    label: str = 'retrieval',
) -> Dict:
    """Compute recall@k globally and broken down by ``source`` bucket."""
    hits = 0
    total = 0
    misses = []
    by_source_hits: Dict[str, int] = defaultdict(int)
    by_source_total: Dict[str, int] = defaultdict(int)

    for qa in qa_pairs:
        if not qa.get('expected_article'):
            continue
        source = qa.get('source', 'unknown')
        results = search_fn(qa['question'], top_k)
        found = any(
            r.get('article_id') == qa['expected_article'] for r in results
        )
        total += 1
        by_source_total[source] += 1
        if found:
            hits += 1
            by_source_hits[source] += 1
        else:
            misses.append({
                'question': qa['question'],
                'expected': qa['expected_article'],
                'got': [r.get('article_id') for r in results],
                'source': source,
            })

    by_source = {
        src: {
            'hits': by_source_hits[src],
            'total': by_source_total[src],
            'recall_at_k': round(by_source_hits[src] / by_source_total[src], 4)
            if by_source_total[src] else 0.0,
        }
        for src in sorted(by_source_total)
    }
    recall = hits / total if total else 0.0
    return {
        'label': label,
        'recall_at_k': round(recall, 4),
        'k': top_k,
        'hits': hits,
        'total': total,
        'by_source': by_source,
        'misses': misses,
    }


def _print_comparison(bm25_res: Dict, hybrid_res: Dict) -> None:
    """Print a compact side-by-side per-source recall table."""
    print()
    print(f'Recall@{bm25_res["k"]}  side-by-side  (BM25 baseline vs Hybrid RRF)')
    print('=' * 76)
    header = f'{"source":<26}{"n":>6}{"BM25":>12}{"Hybrid":>12}{"delta":>12}'
    print(header)
    print('-' * 76)
    sources = sorted(set(bm25_res['by_source']) | set(hybrid_res['by_source']))
    for src in sources:
        b = bm25_res['by_source'].get(src, {'recall_at_k': 0.0, 'total': 0})
        h = hybrid_res['by_source'].get(src, {'recall_at_k': 0.0, 'total': 0})
        n = b.get('total') or h.get('total') or 0
        b_r = b['recall_at_k']
        h_r = h['recall_at_k']
        delta = h_r - b_r
        sign = '+' if delta >= 0 else ''
        print(
            f'{src:<26}{n:>6}{b_r * 100:>11.1f}%{h_r * 100:>11.1f}%'
            f'{sign}{delta * 100:>10.1f}%'
        )
    print('-' * 76)
    b_r = bm25_res['recall_at_k']
    h_r = hybrid_res['recall_at_k']
    delta = h_r - b_r
    sign = '+' if delta >= 0 else ''
    print(
        f'{"OVERALL":<26}{bm25_res["total"]:>6}'
        f'{b_r * 100:>11.1f}%{h_r * 100:>11.1f}%{sign}{delta * 100:>10.1f}%'
    )
    print('=' * 76)


def _api_eval(qa_pairs: List[Dict], api_url: str, strict: bool = False,
              mode: str = 'bm25') -> Dict:
    """Run the /ask endpoint against every QA pair and score:

    - citation_accuracy: for in-scope pairs (expected_article set), how often does
      a citation reference the expected article
    - correct_abstention: for out-of-scope pairs (expected_article None), how
      often does the model correctly abstain
    - false_answer_on_oos: out-of-scope pairs where the model answered anyway
    - unverified_answer_rate: answers with at least one uncited claim
    """
    import urllib.request

    in_scope_total = 0
    in_scope_correct_citation = 0
    in_scope_abstained = 0
    oos_total = 0
    oos_correct_abstention = 0
    unverified = 0
    api_errors = 0
    details: List[Dict] = []

    for qa in qa_pairs:
        payload = json.dumps({
            'query': qa['question'],
            'strict': strict,
            'mode': mode,
        }).encode()
        req = urllib.request.Request(
            f'{api_url}/ask',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            api_errors += 1
            details.append({'id': qa['id'], 'error': str(e)})
            continue

        abstained = data.get('abstained', False)
        citations = data.get('citations', [])
        verified = data.get('verified', True)
        expected = qa.get('expected_article')

        if not verified:
            unverified += 1

        if expected is None:
            oos_total += 1
            if abstained:
                oos_correct_abstention += 1
            else:
                details.append({
                    'id': qa['id'], 'type': 'false_answer_on_oos',
                    'question': qa['question'][:80],
                    'citation_count': len(citations),
                })
        else:
            in_scope_total += 1
            if abstained:
                in_scope_abstained += 1
            elif any(expected in str(c.get('title') or '') or expected in str(c.get('document_id') or '')
                     for c in citations):
                in_scope_correct_citation += 1
            else:
                details.append({
                    'id': qa['id'], 'type': 'wrong_citation',
                    'expected': expected,
                    'got': [c.get('title') for c in citations[:3]],
                })

    in_scope_answered = in_scope_total - in_scope_abstained
    return {
        'mode': mode,
        'citation_accuracy': round(in_scope_correct_citation / max(in_scope_answered, 1), 4),
        'in_scope_answered': in_scope_answered,
        'in_scope_abstained_incorrectly': in_scope_abstained,
        'in_scope_total': in_scope_total,
        'correct_abstention_rate_on_oos': round(oos_correct_abstention / max(oos_total, 1), 4),
        'oos_total': oos_total,
        'unverified_answer_rate': round(unverified / max(in_scope_total + oos_total - api_errors, 1), 4),
        'api_errors': api_errors,
        'strict_mode': strict,
        'details_sample': details[:15],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('qa_pairs', help='Path to QA pairs JSON')
    parser.add_argument('index_or_api', help='Path to inverted_index.json OR --api flag base URL')
    parser.add_argument('--api', action='store_true', help='Treat second arg as API base URL')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--strict', action='store_true',
                        help='Enable strict verification gate on /ask endpoint')
    parser.add_argument(
        '--mode', default='bm25',
        choices=['bm25', 'dense', 'hybrid', 'compare'],
        help=(
            'Retrieval backend. `compare` runs BM25 and hybrid on the same '
            'QA pairs and prints a side-by-side breakdown.'
        ),
    )
    parser.add_argument(
        '--json-out', type=Path, default=None,
        help='Optional path to dump full eval results as JSON.'
    )
    args = parser.parse_args()

    qa_pairs = json.loads(Path(args.qa_pairs).read_text(encoding='utf-8'))
    print(f'Loaded {len(qa_pairs)} QA pairs.')

    if args.api:
        results = _api_eval(
            qa_pairs, args.index_or_api, strict=args.strict, mode=args.mode
            if args.mode != 'compare' else 'bm25',
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))
        if args.json_out:
            args.json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        return

    if args.mode == 'compare':
        index = _load_index(args.index_or_api)
        bm25_res = _retrieval_eval(
            qa_pairs, _bm25_searcher(index), top_k=args.top_k, label='bm25',
        )
        hybrid_res = _retrieval_eval(
            qa_pairs, _hybrid_searcher('hybrid'), top_k=args.top_k, label='hybrid',
        )
        _print_comparison(bm25_res, hybrid_res)
        combined = {
            'bm25': {k: v for k, v in bm25_res.items() if k != 'misses'},
            'hybrid': {k: v for k, v in hybrid_res.items() if k != 'misses'},
            'bm25_misses_sample': bm25_res['misses'][:10],
            'hybrid_misses_sample': hybrid_res['misses'][:10],
        }
        if args.json_out:
            args.json_out.write_text(
                json.dumps(combined, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            print(f'\nFull results written to {args.json_out}')
        return

    # Single-mode retrieval eval
    if args.mode == 'bm25':
        index = _load_index(args.index_or_api)
        search_fn = _bm25_searcher(index)
    else:
        search_fn = _hybrid_searcher(args.mode)

    results = _retrieval_eval(
        qa_pairs, search_fn, top_k=args.top_k, label=args.mode,
    )
    print(json.dumps(
        {k: v for k, v in results.items() if k != 'misses'},
        indent=2, ensure_ascii=False,
    ))
    if results['misses']:
        print(f'\nMissed {len(results["misses"])} questions:')
        for m in results['misses'][:10]:
            print(f'  Q: {m["question"][:80]}')
            print(f'     expected={m["expected"]}, got={m["got"][:3]}')
    if args.json_out:
        args.json_out.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )


if __name__ == '__main__':
    main()
