"""Simple Flask API for RAG retrieval with Claude generation."""
"""Chookaszian Corpus RAG API — Claude Citations endpoint with abstention guard.

Uses BM25 inverted index (rag/inverted_index.json) for retrieval and Claude's
citations feature for grounded answer generation.

Abstention: if max BM25 score < ABSTENTION_THRESHOLD the model receives no
documents and must say it cannot answer from the corpus.

Usage:
    python rag/api.py                  # starts on :5000
    python rag/api.py --port 8080
"""
import json
import os
import sys
import argparse
from pathlib import Path
from flask import Flask, request, jsonify

try:
    import anthropic
except ImportError:
    print("Install: pip install flask anthropic")
    sys.exit(1)

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT.parent))
from rag.indexer import CorpusIndex

INDEX_PATH = _ROOT / 'inverted_index.json'
TOP_K = 5
ABSTENTION_THRESHOLD = 1.5   # BM25 score below which we abstain
CLAUDE_MODEL = 'claude-3-5-sonnet-20241022'

app = Flask(__name__)
_index: CorpusIndex | None = None


def _get_index() -> CorpusIndex:
    global _index
    if _index is None:
        if not INDEX_PATH.exists():
            raise RuntimeError(
                f'Index not found at {INDEX_PATH}. '
                'Run: python rag/chunker.py tei_enriched rag/chunks.json && '
                'python rag/indexer.py rag/chunks.json rag/inverted_index.json'
            )
        _index = CorpusIndex.load(str(INDEX_PATH))
    return _index


@app.route('/health', methods=['GET'])
def health():
    try:
        idx = _get_index()
        return jsonify({'status': 'ok', 'chunks': idx.N})
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 503


@app.route('/search', methods=['POST'])
def search():
    data = request.get_json(force=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({'error': 'query required'}), 400
    top_k = int(data.get('top_k', TOP_K))
    results = _get_index().search(query, top_k=top_k)
    return jsonify({'query': query, 'results': results, 'count': len(results)})


@app.route('/ask', methods=['POST'])
def ask():
    """Retrieve + generate grounded answer with Claude Citations API."""
    data = request.get_json(force=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({'error': 'query required'}), 400

    results = _get_index().search(query, top_k=TOP_K)

    # Abstain if no result exceeds threshold
    if not results or results[0].get('score', 0) < ABSTENTION_THRESHOLD:
        return jsonify({
            'query': query,
            'answer': (
                'The corpus does not contain sufficiently relevant information '
                'to answer this question reliably.'
            ),
            'citations': [],
            'abstained': True,
        })

    # Build document list for Claude Citations
    documents = [
        {
            'type': 'document',
            'id': f'chunk_{r["chunk_index_global"]}',
            'title': f'{r.get("title", r.get("article_id", ""))} (p. {r.get("pages", "")})',
            'content': [{'type': 'text', 'text': r['text']}],
        }
        for r in results
    ]

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=800,
        betas=['citations-2024-11-15'],
        messages=[
            {
                'role': 'user',
                'content': documents + [
                    {
                        'type': 'text',
                        'text': (
                            f'Using only the documents above, answer the following question '
                            f'about the Chookaszian Armenian studies corpus. '
                            f'If the answer is not in the documents, say so explicitly.\n\n'
                            f'Question: {query}'
                        ),
                    }
                ],
            }
        ],
    )

    # Extract text and citations from response
    answer_parts = []
    citations = []
    for block in response.content:
        if block.type == 'text':
            answer_parts.append(block.text)
        elif block.type == 'citations':
            for citation in (block.citations or []):
                citations.append({
                    'document_id': getattr(citation, 'document_id', None),
                    'title': getattr(citation, 'document_title', None),
                    'quote': getattr(citation, 'cited_text', None),
                })

    return jsonify({
        'query': query,
        'answer': ' '.join(answer_parts),
        'citations': citations,
        'abstained': False,
        'chunks_used': len(results),
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    print(f'Starting Chookaszian RAG API on {args.host}:{args.port}')
    app.run(host=args.host, port=args.port, debug=False)
