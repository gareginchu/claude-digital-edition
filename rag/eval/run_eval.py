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


def _api_eval(qa_pairs: List[Dict], api_url: str) -> Dict:
    import urllib.request, urllib.error
    correct_citations = 0
    abstentions = 0
    total = 0
    for qa in qa_pairs:
        payload = json.dumps({'query': qa['question']}).encode()
        req = urllib.request.Request(
            f'{api_url}/ask',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f'  API error: {e}')
            continue
        total += 1
        answer = data.get('answer', '')
        citations = data.get('citations', [])
        if 'does not contain' in answer.lower() or not citations:
            abstentions += 1
            continue
        if 'expected_article' in qa:
            if any(qa['expected_article'] in str(c) for c in citations):
                correct_citations += 1
    return {
        'citation_accuracy': round(correct_citations / max(total - abstentions, 1), 4),
        'abstention_rate': round(abstentions / max(total, 1), 4),
        'total': total,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('qa_pairs', help='Path to QA pairs JSON')
    parser.add_argument('index_or_api', help='Path to inverted_index.json OR --api flag base URL')
    parser.add_argument('--api', action='store_true', help='Treat second arg as API base URL')
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()

    qa_pairs = json.loads(Path(args.qa_pairs).read_text(encoding='utf-8'))
    print(f'Loaded {len(qa_pairs)} QA pairs.')

    if args.api:
        results = _api_eval(qa_pairs, args.index_or_api)
        print(json.dumps(results, indent=2))
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
