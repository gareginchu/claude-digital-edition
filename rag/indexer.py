"""JSON-backed full-text index for the Chookaszian corpus.

Uses a simple inverted index with TF-IDF-style scoring as a local fallback
that works without a running Postgres/pgvector. When pgvector is available,
use embed_and_index.py for dense vector retrieval.

Usage:
    from rag.indexer import CorpusIndex
    idx = CorpusIndex.build('rag/chunks.json')
    idx.save('rag/inverted_index.json')
    # later:
    idx = CorpusIndex.load('rag/inverted_index.json')
    results = idx.search('Grigor Narekatsi poem', top_k=5)
"""
from __future__ import annotations
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional


def _tokenize(text: str) -> List[str]:
    text = unicodedata.normalize('NFC', text.lower())
    return [t for t in re.findall(r'[\u0561-\u0587\u0531-\u0556a-z]+', text) if len(t) > 1]


class CorpusIndex:
    """Inverted index with BM25 scoring over corpus chunks."""

    K1 = 1.5
    B = 0.75

    def __init__(self, chunks: List[Dict], inv_index: Dict, df: Dict, avg_dl: float):
        self.chunks = chunks  # list of chunk dicts
        self.inv_index = inv_index  # token -> {chunk_idx: term_freq}
        self.df = df            # token -> doc_freq
        self.avg_dl = avg_dl   # average document length in tokens
        self.N = len(chunks)

    @classmethod
    def build(cls, chunks_json: str) -> 'CorpusIndex':
        chunks = json.loads(Path(chunks_json).read_text(encoding='utf-8'))
        inv_index: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        doc_lengths = []
        for i, chunk in enumerate(chunks):
            tokens = _tokenize(chunk.get('text', ''))
            doc_lengths.append(len(tokens))
            for tok in tokens:
                inv_index[tok][i] += 1
        df = {tok: len(postings) for tok, postings in inv_index.items()}
        avg_dl = sum(doc_lengths) / max(len(doc_lengths), 1)
        # Convert defaultdicts to plain dicts for serialization
        inv_index_plain = {t: dict(p) for t, p in inv_index.items()}
        return cls(chunks, inv_index_plain, df, avg_dl)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        tokens = _tokenize(query)
        scores: Dict[int, float] = defaultdict(float)
        for tok in tokens:
            if tok not in self.inv_index:
                continue
            idf = math.log((self.N - self.df[tok] + 0.5) / (self.df[tok] + 0.5) + 1)
            for chunk_idx, tf in self.inv_index[tok].items():
                dl = len(_tokenize(self.chunks[chunk_idx].get('text', '')))
                tf_norm = (tf * (self.K1 + 1)) / (tf + self.K1 * (1 - self.B + self.B * dl / self.avg_dl))
                scores[chunk_idx] += idf * tf_norm
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {
                **self.chunks[i],
                'score': round(score, 4),
                'chunk_index_global': i,
            }
            for i, score in ranked
        ]

    def save(self, path: str):
        Path(path).write_text(
            json.dumps({
                'chunks': self.chunks,
                'inv_index': self.inv_index,
                'df': self.df,
                'avg_dl': self.avg_dl,
            }, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        print(f'Saved index: {path} ({self.N} chunks, {len(self.inv_index)} terms)')

    @classmethod
    def load(cls, path: str) -> 'CorpusIndex':
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        # JSON serialises int dict keys as strings; cast back to int
        inv_index = {tok: {int(k): v for k, v in postings.items()}
                     for tok, postings in data['inv_index'].items()}
        return cls(
            chunks=data['chunks'],
            inv_index=inv_index,
            df=data['df'],
            avg_dl=data['avg_dl'],
        )


# Compatibility shim for existing code calling write_index
def write_index(chunks, out_path):
    Path(out_path).write_text(json.dumps({'chunks': chunks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: indexer.py <chunks.json> [inverted_index.json]')
        sys.exit(1)
    idx = CorpusIndex.build(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else 'rag/inverted_index.json'
    idx.save(out)
