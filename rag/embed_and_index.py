"""RAG with BGE-M3 embeddings and pgvector storage."""
import json
from pathlib import Path
from typing import List, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import psycopg
except ImportError:
    print("⚠️  Install: pip install sentence-transformers psycopg[binary]")

class RAGEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """Load BGE-M3 model for multilingual embeddings (Armenian, Russian, French)."""
        print(f"Loading {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed_chunks(self, chunks: List[str]) -> np.ndarray:
        """Embed list of text chunks. Returns (n_chunks, 384) array."""
        print(f"Embedding {len(chunks)} chunks...")
        embeddings = self.model.encode(chunks, show_progress_bar=True, normalize_embeddings=True)
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed single query."""
        return self.model.encode(query, normalize_embeddings=True)

def load_index(index_path: str) -> Dict:
    """Load RAG index from rag/index.json."""
    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_pgvector_index(index_json: str, db_url: str = "postgresql://localhost/chookaszian"):
    """Create pgvector index from RAG chunks."""
    print(f"Connecting to {db_url}...")
    
    try:
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("To set up locally:")
        print("  1. Install PostgreSQL")
        print("  2. Create DB: createdb chookaszian")
        print("  3. Enable pgvector: psql chookaszian -c 'CREATE EXTENSION IF NOT EXISTS vector'")
        print("  4. Run: python rag/embed_and_index.py")
        return
    
    # Create table with vector column
    cur.execute("""
        DROP TABLE IF EXISTS chunks CASCADE;
        CREATE TABLE chunks (
            id SERIAL PRIMARY KEY,
            article_id INTEGER,
            chunk_id TEXT UNIQUE,
            text TEXT,
            embedding vector(384),
            token_count INTEGER
        );
        CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    """)
    
    # Load index and embed chunks
    index = load_index(index_json)
    chunk_texts = [c['text'][:500] for c in index['chunks']]  # Truncate for embedding
    
    embedder = RAGEmbedder()
    embeddings = embedder.embed_chunks(chunk_texts)
    
    # Insert into pgvector
    print("Inserting chunks into database...")
    for i, chunk in enumerate(index['chunks']):
        embedding_str = embeddings[i].tolist()
        cur.execute(
            """
            INSERT INTO chunks (article_id, chunk_id, text, embedding, token_count)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (chunk['article_id'], chunk['id'], chunk['text'][:500], embedding_str, chunk['token_count'])
        )
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Indexed {len(index['chunks'])} chunks in pgvector")

def retrieve(query: str, db_url: str = "postgresql://localhost/chookaszian", top_k: int = 5) -> List[Dict]:
    """Retrieve top-k chunks similar to query."""
    embedder = RAGEmbedder()
    query_emb = embedder.embed_query(query)
    
    try:
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
    except:
        print("❌ Cannot connect to database")
        return []
    
    # Vector similarity search
    cur.execute(
        """
        SELECT id, article_id, chunk_id, text, 1 - (embedding <=> %s) as similarity
        FROM chunks
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (query_emb.tolist(), query_emb.tolist(), top_k)
    )
    
    results = []
    for row in cur.fetchall():
        results.append({
            'id': row[0],
            'article_id': row[1],
            'chunk_id': row[2],
            'text': row[3],
            'similarity': float(row[4])
        })
    
    cur.close()
    conn.close()
    return results

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rag/embed_and_index.py index       # Build pgvector index")
        print("  python rag/embed_and_index.py query <text> # Query embeddings")
    elif sys.argv[1] == 'index':
        create_pgvector_index('rag/index.json')
    elif sys.argv[1] == 'query':
        query = ' '.join(sys.argv[2:])
        results = retrieve(query)
        print(f"Top results for: {query}")
        for r in results:
            print(f"  [{r['similarity']:.2f}] {r['text'][:100]}...")
