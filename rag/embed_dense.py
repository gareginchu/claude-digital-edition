"""Dense embedding pipeline for the Chookaszian corpus.

Reads ``rag/chunks.json``, embeds each chunk's text with BGE-M3
(``BAAI/bge-m3``) via sentence-transformers, and writes the resulting
vectors into a ChromaDB persistent collection under ``rag/chroma/``.

Design notes (CLAUDE.md Phase 5 + user-chosen backend):
- ChromaDB was chosen instead of pgvector because this project is a
  static-first scholarly edition; the vector store is embedded, file-based
  and disposable. The BM25 index (``rag/inverted_index.json``) remains
  authoritative for the sparse layer and is NOT modified by this script.
- BGE-M3 dense output only in this pass. The model also emits a sparse
  representation, but wiring that in requires the ``FlagEmbedding`` package
  and additional storage; deferred until we have a clean interface.
- The reranker (``bge-reranker-v2-m3``) is out of scope for this script.
  See :func:`rag.hybrid_retrieve.rerank_stub` for the CPU-vs-GPU note.
- We pre-translate Armenian chunks with the same transliteration table
  the chunker already applies at the prefix boundary. BGE-M3 is
  multilingual and handles Armenian script natively, so we simply feed
  the raw chunk text (which already carries a transliterated ``Persons``
  suffix from ``rag/chunker.py``).

Usage::

    python rag/embed_dense.py                       # default paths
    python rag/embed_dense.py --chunks rag/chunks.json \
        --persist rag/chroma --collection bc_dense \
        --batch-size 8 --limit 20
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterable, List

_ROOT = Path(__file__).parent
DEFAULT_CHUNKS = _ROOT / 'chunks.json'
DEFAULT_PERSIST = _ROOT / 'chroma'
DEFAULT_COLLECTION = 'bc_dense'
DEFAULT_MODEL = 'BAAI/bge-m3'
DEFAULT_BATCH = 8


def _load_chunks(chunks_path: Path) -> List[dict]:
    if not chunks_path.exists():
        raise FileNotFoundError(
            f'Chunks file not found at {chunks_path}. '
            f'Run: python rag/chunker.py tei_enriched rag/chunks.json'
        )
    return json.loads(chunks_path.read_text(encoding='utf-8'))


def _chunk_id(chunk: dict) -> str:
    return f'chunk_{chunk["article_id"]}_{chunk["chunk_index"]}'


def _chunk_metadata(chunk: dict) -> dict:
    # ChromaDB requires scalar metadata values (str, int, float, bool).
    return {
        'article_id': str(chunk.get('article_id', '')),
        'chunk_index': int(chunk.get('chunk_index', 0)),
        'title': str(chunk.get('title', '')),
        'pages': str(chunk.get('pages', '')),
    }


def _batched(iterable: List, n: int) -> Iterable[List]:
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]


def build_collection(
    chunks_path: Path = DEFAULT_CHUNKS,
    persist_dir: Path = DEFAULT_PERSIST,
    collection_name: str = DEFAULT_COLLECTION,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH,
    limit: int | None = None,
    reset: bool = True,
) -> dict:
    """Embed chunks and (re)build the Chroma collection.

    Returns a stats dict with wall-clock timings for reporting.
    """
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError(
            'Missing dependency; install with `pip install chromadb sentence-transformers`.'
        ) from e

    chunks = _load_chunks(chunks_path)
    if limit:
        chunks = chunks[:limit]

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    # Cosine similarity is standard for BGE-M3 (paper-recommended).
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={'hnsw:space': 'cosine', 'model': model_name},
    )

    t_model_start = time.time()
    print(f'Loading model {model_name} (first run downloads ~2GB)...')
    model = SentenceTransformer(model_name)
    t_model_load = time.time() - t_model_start
    print(f'Model loaded in {t_model_load:.1f}s.')

    ids = [_chunk_id(c) for c in chunks]
    metadatas = [_chunk_metadata(c) for c in chunks]
    documents = [c['text'] for c in chunks]

    t_embed_start = time.time()
    total_batches = (len(documents) + batch_size - 1) // batch_size
    print(
        f'Embedding {len(documents)} chunks in {total_batches} batches '
        f'of {batch_size}...'
    )

    n_written = 0
    for batch_i, (batch_docs, batch_ids, batch_meta) in enumerate(zip(
        _batched(documents, batch_size),
        _batched(ids, batch_size),
        _batched(metadatas, batch_size),
    ), start=1):
        batch_start = time.time()
        vectors = model.encode(
            batch_docs,
            normalize_embeddings=True,   # unit-length for cosine
            show_progress_bar=False,
        )
        # sentence-transformers returns numpy; Chroma accepts a list-of-list.
        collection.upsert(
            ids=batch_ids,
            embeddings=[v.tolist() for v in vectors],
            documents=batch_docs,
            metadatas=batch_meta,
        )
        n_written += len(batch_docs)
        elapsed = time.time() - batch_start
        print(
            f'  batch {batch_i}/{total_batches}  '
            f'({n_written}/{len(documents)} chunks, {elapsed:.1f}s)'
        )

    t_embed = time.time() - t_embed_start
    stats = {
        'model': model_name,
        'chunks_embedded': n_written,
        'collection': collection_name,
        'persist_dir': str(persist_dir),
        'model_load_seconds': round(t_model_load, 2),
        'embed_wallclock_seconds': round(t_embed, 2),
        'batch_size': batch_size,
    }
    print('Done.')
    print(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chunks', type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument('--persist', type=Path, default=DEFAULT_PERSIST)
    parser.add_argument('--collection', default=DEFAULT_COLLECTION)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH)
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Embed only the first N chunks (smoke-test flag).'
    )
    parser.add_argument(
        '--no-reset', action='store_true',
        help='Do not delete the existing collection before writing.'
    )
    args = parser.parse_args()

    build_collection(
        chunks_path=args.chunks,
        persist_dir=args.persist,
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
        limit=args.limit,
        reset=not args.no_reset,
    )


if __name__ == '__main__':
    sys.exit(main())
