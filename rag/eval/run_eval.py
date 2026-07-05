"""Eval harness for the Chookaszian corpus RAG pipeline.

Runs a set of QA pairs against the retrieval index and the /ask API endpoint,
computing:
  - Retrieval recall@k: does the correct article appear in top-k results?
  - Answer citation accuracy: does the answer cite the correct source?
  - Abstention rate: how often does the model correctly say "I don't know"?

Usage:
    python rag/eval/run_eval.py rag/eval/qa_pairs.json rag/inverted_index.json
    python rag/eval/run_eval.py --api http://localhost:5000 rag/eval/qa_pairs.json
"""
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict


def _load_index(index_path: str):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.indexer import CorpusIndex
    return CorpusIndex.load(index_path)


def _retrieval_eval(qa_pairs: List[Dict], index, top_k: int = 5) -> Dict:
    hits = 0
    total = 0
    misses = []
    for qa in qa_pairs:
        if 'expected_article' not in qa:
            continue
        results = index.search(qa['question'], top_k=top_k)
        found = any(r.get('article_id') == qa['expected_article'] for r in results)
        if found:
            hits += 1
        else:
            misses.append({'question': qa['question'], 'expected': qa['expected_article'],
                           'got': [r.get('article_id') for r in results]})
        total += 1
    recall = hits / total if total else 0.0
    return {'recall_at_k': round(recall, 4), 'k': top_k, 'hits': hits, 'total': total, 'misses': misses}


def _api_eval(qa_pairs: List[Dict], api_url: str, strict: bool = False) -> Dict:
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
        payload = json.dumps({'query': qa['question'], 'strict': strict}).encode()
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
    args = parser.parse_args()

    qa_pairs = json.loads(Path(args.qa_pairs).read_text(encoding='utf-8'))
    print(f'Loaded {len(qa_pairs)} QA pairs.')

    if args.api:
        results = _api_eval(qa_pairs, args.index_or_api, strict=args.strict)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        index = _load_index(args.index_or_api)
        results = _retrieval_eval(qa_pairs, index, top_k=args.top_k)
        print(json.dumps(results, indent=2))
        if results['misses']:
            print(f'\nMissed {len(results["misses"])} questions:')
            for m in results['misses'][:10]:
                print(f'  Q: {m["question"][:80]}')
                print(f'     expected={m["expected"]}, got={m["got"][:3]}')


if __name__ == '__main__':
    main()
