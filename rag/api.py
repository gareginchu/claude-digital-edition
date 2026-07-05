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

# Load .env at import time so ANTHROPIC_API_KEY (and any Chroma/BGE knobs)
# reach the anthropic SDK before the first client instantiation.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

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

# Retrieval backends selectable at request time.
#   'bm25'   - historical default; only backend that trips the abstention gate
#   'dense'  - BGE-M3 similarity via ChromaDB
#   'hybrid' - RRF fusion of bm25 + dense
# Abstention thresholds are calibrated against BM25 scores; for non-BM25
# modes we fall back to a conservative "abstain iff no results" policy.
VALID_MODES = {'bm25', 'dense', 'hybrid'}
DEFAULT_MODE = 'bm25'

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


def _resolve_mode(data: dict) -> str:
    mode = (data.get('mode') or DEFAULT_MODE).lower().strip()
    if mode not in VALID_MODES:
        return DEFAULT_MODE
    return mode


def _retrieve(query: str, top_k: int, mode: str) -> list[dict]:
    """Dispatch to BM25 (existing behaviour) or the hybrid module."""
    if mode == 'bm25':
        return _get_index().search(query, top_k=top_k)
    # Lazy import so BM25-only deployments do not need chromadb / torch.
    from rag.hybrid_retrieve import hybrid_search
    return hybrid_search(query, top_k=top_k, mode=mode)


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
    mode = _resolve_mode(data)
    try:
        results = _retrieve(query, top_k=top_k, mode=mode)
    except Exception as e:
        return jsonify({'error': f'retrieval failed ({mode}): {e}'}), 500
    return jsonify({
        'query': query,
        'mode': mode,
        'results': results,
        'count': len(results),
    })


@app.route('/ask', methods=['POST'])
def ask():
    """Retrieve + generate grounded answer with Claude Citations API."""
    data = request.get_json(force=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({'error': 'query required'}), 400

    mode = _resolve_mode(data)
    try:
        results = _retrieve(query, top_k=TOP_K, mode=mode)
    except Exception as e:
        return jsonify({'error': f'retrieval failed ({mode}): {e}'}), 500

    # Abstention gate. BM25 uses a calibrated score threshold; hybrid/dense
    # scores are not comparable, so we fall back to "abstain iff empty".
    if mode == 'bm25':
        low_confidence = (
            not results or results[0].get('score', 0) < ABSTENTION_THRESHOLD
        )
    else:
        low_confidence = not results

    if low_confidence:
        return jsonify({
            'query': query,
            'mode': mode,
            'answer': (
                'The corpus does not contain sufficiently relevant information '
                'to answer this question reliably.'
            ),
            'citations': [],
            'abstained': True,
        })

    # Build document list for Claude Citations. Hybrid / dense hits do not
    # carry the BM25 global chunk index; fall back to article_id + chunk_index.
    def _doc_id(hit: dict, i: int) -> str:
        if 'chunk_index_global' in hit:
            return f'chunk_{hit["chunk_index_global"]}'
        return f'chunk_{hit.get("article_id", "?")}_{hit.get("chunk_index", i)}'

    documents = [
        {
            'type': 'document',
            'id': _doc_id(r, i),
            'title': f'{r.get("title", r.get("article_id", ""))} (p. {r.get("pages", "")})',
            'content': [{'type': 'text', 'text': r['text']}],
        }
        for i, r in enumerate(results)
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

    # Extract text and citations. In the Anthropic Citations API each text
    # block carries its own citations list; a text block with no citations is
    # an uncited claim (LettuceDetect-style verification gate).
    answer_parts: list[str] = []
    citations: list[dict] = []
    uncited_spans: list[str] = []
    for block in response.content:
        if getattr(block, 'type', None) != 'text':
            continue
        text = getattr(block, 'text', '') or ''
        answer_parts.append(text)
        block_citations = getattr(block, 'citations', None) or []
        if text.strip() and not block_citations:
            # Non-empty text with no supporting citation.
            uncited_spans.append(text.strip())
        for citation in block_citations:
            citations.append({
                'document_id': getattr(citation, 'document_id', None),
                'title': getattr(citation, 'document_title', None),
                'quote': getattr(citation, 'cited_text', None),
            })

    verified = len(uncited_spans) == 0
    strict = (data.get('strict') or '').lower() == 'true' or data.get('strict') is True
    if not verified and strict:
        return jsonify({
            'query': query,
            'mode': mode,
            'answer': (
                'The corpus cannot support a fully-cited answer to this question. '
                'Verification gate rejected the response.'
            ),
            'citations': [],
            'abstained': True,
            'reason': 'uncited_claims',
            'uncited_spans': uncited_spans,
        })

    return jsonify({
        'query': query,
        'mode': mode,
        'answer': ' '.join(answer_parts),
        'citations': citations,
        'abstained': False,
        'verified': verified,
        'uncited_span_count': len(uncited_spans),
        'uncited_spans': uncited_spans if not verified else [],
        'chunks_used': len(results),
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    print(f'Starting Chookaszian RAG API on {args.host}:{args.port}')
    app.run(host=args.host, port=args.port, debug=False)
