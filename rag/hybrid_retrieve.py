"""Hybrid retrieval for the Chookaszian corpus.

Combines the existing BM25 :class:`rag.indexer.CorpusIndex` with dense
BGE-M3 vectors stored in ChromaDB (built by :mod:`rag.embed_dense`).
Fusion uses Reciprocal Rank Fusion (RRF, k=60), the standard robust
recipe for combining ranked lists with incomparable scores.

Design rationale:
- CLAUDE.md prescribes BGE-M3 dense + BM25 hybrid retrieval; ChromaDB is
  the user-chosen embedded backend replacing pgvector.
- The BM25 index remains authoritative on lexical / romanized queries.
  Dense catches the curated / cross-lingual (English query, Armenian
  corpus) surface-mismatch cases where BM25 recall is weak.
- We deliberately do NOT re-tokenize or re-normalize inside the retriever;
  the BM25 index already handles NFC + Armenian/Latin token unification,
  and BGE-M3 is trained multilingual so raw chunk text is fine.

Modes:
  ``bm25``   - existing lexical retrieval only (baseline, unchanged)
  ``dense``  - BGE-M3 similarity from ChromaDB only
  ``hybrid`` - RRF fusion of ``bm25`` and ``dense`` top-K lists

Usage::

    from rag.hybrid_retrieve import hybrid_search
    results = hybrid_search('Grigor Narekatsi poem', top_k=5, mode='hybrid')
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).parent
DEFAULT_INDEX = _ROOT / 'inverted_index.json'
DEFAULT_PERSIST = _ROOT / 'chroma'
DEFAULT_COLLECTION = 'bc_dense'
DEFAULT_MODEL = 'BAAI/bge-m3'

# RRF constant. 60 is the value from the original Cormack et al. 2009 paper
# and the de-facto default across the retrieval literature.
RRF_K = 60

# Over-retrieve from each leg before fusing so RRF has something to rank.
CANDIDATE_DEPTH = 20


def _chunk_key(chunk_meta: Dict) -> str:
    return f'{chunk_meta.get("article_id", "")}::{chunk_meta.get("chunk_index", 0)}'


@lru_cache(maxsize=1)
def _bm25_index():
    from rag.indexer import CorpusIndex
    if not DEFAULT_INDEX.exists():
        raise RuntimeError(
            f'BM25 index missing at {DEFAULT_INDEX}. '
            'Run: python rag/indexer.py rag/chunks.json rag/inverted_index.json'
        )
    return CorpusIndex.load(str(DEFAULT_INDEX))


@lru_cache(maxsize=1)
def _dense_collection():
    import chromadb
    if not DEFAULT_PERSIST.exists():
        raise RuntimeError(
            f'Chroma persist dir missing at {DEFAULT_PERSIST}. '
            'Run: python rag/embed_dense.py'
        )
    client = chromadb.PersistentClient(path=str(DEFAULT_PERSIST))
    return client.get_collection(DEFAULT_COLLECTION)


@lru_cache(maxsize=1)
def _embed_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(DEFAULT_MODEL)


def _bm25_search(query: str, top_k: int) -> List[Dict]:
    return _bm25_index().search(query, top_k=top_k)


def _dense_search(query: str, top_k: int) -> List[Dict]:
    """Query ChromaDB with a BGE-M3 embedding of the input string."""
    model = _embed_model()
    q_vec = model.encode(
        [query], normalize_embeddings=True, show_progress_bar=False
    )[0].tolist()
    coll = _dense_collection()
    res = coll.query(
        query_embeddings=[q_vec],
        n_results=top_k,
        include=['documents', 'metadatas', 'distances'],
    )
    # Chroma returns list-of-lists (per query); we always send one query.
    docs = (res.get('documents') or [[]])[0]
    metas = (res.get('metadatas') or [[]])[0]
    dists = (res.get('distances') or [[]])[0]
    hits: List[Dict] = []
    for doc, meta, dist in zip(docs, metas, dists):
        # Cosine distance in [0, 2]; convert to similarity in [-1, 1].
        similarity = 1.0 - float(dist)
        hits.append({
            'article_id': meta.get('article_id'),
            'chunk_index': meta.get('chunk_index'),
            'title': meta.get('title'),
            'pages': meta.get('pages'),
            'text': doc,
            'score': round(similarity, 4),
            'source': 'dense',
        })
    return hits


def _rrf_fuse(rank_lists: List[List[Dict]], top_k: int, k: int = RRF_K) -> List[Dict]:
    """Reciprocal Rank Fusion of two or more ranked result lists.

    RRF score for a document d across lists L_1..L_n is:
        sum_i 1 / (k + rank_i(d))
    where rank starts at 1. Documents absent from a list contribute 0.
    """
    fused_scores: Dict[str, float] = {}
    fused_records: Dict[str, Dict] = {}
    per_source_rank: Dict[str, Dict[str, int]] = {}

    for list_idx, hits in enumerate(rank_lists):
        source_name = f'list_{list_idx}'
        for rank, hit in enumerate(hits, start=1):
            key = _chunk_key(hit)
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank)
            per_source_rank.setdefault(key, {})[source_name] = rank
            # First occurrence keeps its fields; later occurrences overwrite
            # missing keys only.
            if key not in fused_records:
                fused_records[key] = dict(hit)
            else:
                for field, value in hit.items():
                    if field not in fused_records[key] or fused_records[key][field] in (None, ''):
                        fused_records[key][field] = value

    ranked = sorted(fused_scores.items(), key=lambda kv: kv[1], reverse=True)
    output: List[Dict] = []
    for key, score in ranked[:top_k]:
        record = dict(fused_records[key])
        record['score'] = round(score, 6)
        record['rrf_score'] = round(score, 6)
        record['rank_sources'] = per_source_rank.get(key, {})
        output.append(record)
    return output


def hybrid_search(
    query: str,
    top_k: int = 5,
    mode: str = 'hybrid',
    candidate_depth: int = CANDIDATE_DEPTH,
) -> List[Dict]:
    """Public retrieval entry point.

    Parameters
    ----------
    query:
        Free-text query, any language mix the corpus supports.
    top_k:
        Number of results to return after fusion.
    mode:
        ``'bm25'`` (baseline, unchanged), ``'dense'`` (BGE-M3 only) or
        ``'hybrid'`` (RRF-fused). Unknown modes raise ``ValueError``.
    candidate_depth:
        How many candidates to pull from each leg before fusing. Must be
        at least ``top_k``.
    """
    mode = (mode or 'bm25').lower().strip()
    if mode not in {'bm25', 'dense', 'hybrid'}:
        raise ValueError(f'unknown retrieval mode: {mode!r}')

    depth = max(candidate_depth, top_k)

    if mode == 'bm25':
        return _bm25_search(query, top_k=top_k)

    if mode == 'dense':
        return _dense_search(query, top_k=top_k)

    # hybrid
    bm25_hits = _bm25_search(query, top_k=depth)
    dense_hits = _dense_search(query, top_k=depth)
    fused = _rrf_fuse([bm25_hits, dense_hits], top_k=top_k)
    return fused


# ---------------------------------------------------------------------------
# Reranker stub
# ---------------------------------------------------------------------------
def rerank_stub(query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
    """Placeholder for a cross-encoder reranker (bge-reranker-v2-m3).

    The reranker is a >500MB cross-encoder that scores (query, chunk)
    pairs one at a time. On CPU it adds ~2-5s per query per candidate,
    which pushes recall@k evaluation into the tens of minutes for our
    120 QA pairs. It also delivers most of its benefit on GPUs where
    batches of 32+ pairs run in milliseconds.

    TODO: enable when GPU available. Reference implementation::

        from FlagEmbedding import FlagReranker
        reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
        pairs = [[query, c['text']] for c in candidates]
        scores = reranker.compute_score(pairs, normalize=True)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [dict(c, rerank_score=s) for c, s in ranked[:top_k]]

    For now this function is a no-op that returns ``candidates[:top_k]``.
    """
    return candidates[:top_k]


if __name__ == '__main__':  # pragma: no cover - smoke test
    import argparse
    import json as _json
    parser = argparse.ArgumentParser()
    parser.add_argument('query')
    parser.add_argument('--mode', default='hybrid', choices=['bm25', 'dense', 'hybrid'])
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()
    hits = hybrid_search(args.query, top_k=args.top_k, mode=args.mode)
    print(_json.dumps(
        [{k: v for k, v in h.items() if k != 'text'} for h in hits],
        indent=2, ensure_ascii=False,
    ))
