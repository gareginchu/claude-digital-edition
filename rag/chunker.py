"""Simple chunker placeholder: keep article boundaries and small chunks."""
from typing import List

def chunk_text(text: str, max_tokens: int = 500) -> List[str]:
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    chunks = []
    cur = []
    for p in paragraphs:
        cur.append(p)
        if len(' '.join(cur)) > 1000:
            chunks.append('\n\n'.join(cur))
            cur = []
    if cur:
        chunks.append('\n\n'.join(cur))
    return chunks
