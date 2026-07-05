"""Quick setup for RAG embeddings and retrieval."""
import json
import subprocess
import sys
from pathlib import Path

def setup_rag():
    """One-command RAG setup."""
    print("=== Chookaszian Corpus RAG Setup ===\n")
    
    # Step 1: Install dependencies
    print("1️⃣  Installing dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'sentence-transformers', 'psycopg[binary]', 'flask', 'anthropic'])
    print("   ✅ Installed: sentence-transformers, psycopg, flask, anthropic\n")
    
    # Step 2: Setup PostgreSQL + pgvector
    print("2️⃣  PostgreSQL + pgvector setup (manual):")
    print("   a) Install PostgreSQL: https://www.postgresql.org/download/")
    print("   b) Create database: psql -U postgres")
    print("      > CREATE DATABASE chookaszian;")
    print("      > \\c chookaszian")
    print("      > CREATE EXTENSION IF NOT EXISTS vector;")
    print("      > \\q")
    print("   c) Test connection: python rag/embed_and_index.py query test\n")
    
    # Step 3: Download model
    print("3️⃣  Download BGE-M3 (first time only):")
    print("   python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer(\"BAAI/bge-m3\")'")
    print("   ⏱️  Downloads ~1GB, takes ~2-5 min\n")
    
    # Step 4: Build index
    print("4️⃣  Build pgvector index:")
    print("   python rag/embed_and_index.py index")
    print("   ⏱️  Embeds 1685 chunks, takes ~5-10 min\n")
    
    # Step 5: Start API
    print("5️⃣  Start RAG API:")
    print("   python rag/api.py")
    print("   📍 Opens on http://localhost:5000\n")
    
    # Step 6: Test
    print("6️⃣  Test retrieval (in another terminal):")
    print('   curl -X POST http://localhost:5000/ask -H "Content-Type: application/json" -d \'{"query": "What did Chookaszian write about Matenadaran?"}\'')
    print()

def quick_test():
    """Test without database (uses in-memory index)."""
    index_path = Path(__file__).parent / 'index.json'
    if not index_path.exists():
        print("❌ rag/index.json not found")
        return
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    print(f"✅ Index loaded: {len(index['articles'])} articles, {len(index['chunks'])} chunks")
    print(f"   Sample chunk: {index['chunks'][0]['text'][:100]}...")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        quick_test()
    else:
        setup_rag()
