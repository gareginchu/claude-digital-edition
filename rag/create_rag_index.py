"""Minimal RAG index builder: chunk text and create search metadata."""
import json
from pathlib import Path
from typing import List, Dict

def create_rag_index(tei_dir: str, out_json: str):
    """Index TEI files into chunks with metadata."""
    index_data = {
        "articles": [],
        "chunks": []
    }
    
    for i, tei_file in enumerate(sorted(Path(tei_dir).glob('*.xml')), start=1):
        slug = tei_file.stem
        text = tei_file.read_text(encoding='utf-8')
        
        # Store article metadata
        article_meta = {
            "id": slug,
            "title": f"Article {i}",
            "source_file": tei_file.name
        }
        index_data["articles"].append(article_meta)
        
        # Create chunks (simple: split by paragraph markers or every 500 chars)
        chunks = []
        words = text.split()
        current_chunk = []
        for word in words:
            current_chunk.append(word)
            if len(' '.join(current_chunk)) > 500:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        for j, chunk in enumerate(chunks):
            index_data["chunks"].append({
                "id": f"{slug}_chunk_{j}",
                "article_id": slug,
                "text": chunk[:1000],
                "token_count": len(chunk.split())
            })
    
    Path(out_json).write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Created RAG index: {out_json} ({len(index_data['articles'])} articles, {len(index_data['chunks'])} chunks)")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: create_rag_index.py tei_dir output.json")
    else:
        create_rag_index(sys.argv[1], sys.argv[2])
