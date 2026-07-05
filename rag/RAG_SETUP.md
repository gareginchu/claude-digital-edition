# RAG Retrieval Setup

Build a retrieval-augmented generation system for the Chookaszian corpus.

## Quick Start

```bash
# Step 1: Install Python deps
pip install sentence-transformers psycopg[binary] flask anthropic

# Step 2: Set up PostgreSQL locally (one-time)
# See instructions below

# Step 3: Download BGE-M3 model (first time only, ~1GB, takes 2-5 min)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

# Step 4: Build embeddings + pgvector index (5-10 min)
python rag/embed_and_index.py index

# Step 5: Start API server
python rag/api.py

# Step 6: Test in another terminal
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What did Chookaszian write about Matenadaran?"}'
```

## PostgreSQL Setup (one-time)

### On Windows:
1. Download: https://www.postgresql.org/download/windows/
2. Run installer, set password for `postgres` user
3. Open **SQL Shell (psql)**:
   ```sql
   \c postgres
   CREATE DATABASE chookaszian;
   \c chookaszian
   CREATE EXTENSION IF NOT EXISTS vector;
   \q
   ```

### On macOS:
```bash
brew install postgresql
brew services start postgresql
createdb chookaszian
psql chookaszian
  > CREATE EXTENSION IF NOT EXISTS vector;
  > \q
```

### On Linux:
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb chookaszian
sudo -u postgres psql chookaszian
  > CREATE EXTENSION IF NOT EXISTS vector;
  > \q
```

## Architecture

- **Model:** BGE-M3 (multilingual, 384 dims, fast, free)
  - Handles: Armenian (hy), Russian (ru), French (fr), English (en)
  - Normalization: L2-normalized cosine similarity
- **Storage:** PostgreSQL + pgvector extension (IVFFlat index for fast search)
- **API:** Flask with `/search` (embedding-only) and `/ask` (generation) endpoints
- **Generation:** Claude 3.5 Sonnet with in-context retrieval results

## Endpoints

### `/search` (POST)
Retrieve similar chunks without generation.

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Matenadaran", "top_k": 5}'
```

Response:
```json
{
  "query": "Matenadaran",
  "results": [
    {
      "id": 142,
      "article_id": 5,
      "chunk_id": "chunk_231",
      "text": "Մատենադարան....",
      "similarity": 0.87
    }
  ],
  "count": 1
}
```

### `/ask` (POST)
Retrieve + generate answer with Claude.

```bash
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about Chookaszian's work on biblical texts"}'
```

Response:
```json
{
  "query": "Tell me about Chookaszian's work on biblical texts",
  "answer": "According to the corpus, Chookaszian wrote extensively on... [chunk_231, chunk_445]",
  "citations": [
    {
      "article_id": 5,
      "chunk_id": "chunk_231",
      "similarity": 0.87,
      "text": "..."
    }
  ]
}
```

## Environment

Set `ANTHROPIC_API_KEY` for Claude generation:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python rag/api.py
```

## Troubleshooting

**"psycopg.OperationalError: could not connect to server"**
- Check PostgreSQL is running: `psql --version`
- On Windows: Start SQL Server from Services
- On macOS: `brew services start postgresql`
- On Linux: `sudo systemctl start postgresql`

**"ModuleNotFoundError: No module named 'sentence_transformers'"**
- Install: `pip install sentence-transformers`

**Model download fails**
- Check internet connection
- Manual download: `python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('BAAI/bge-m3'); print(m.get_sentence_embedding_dimension())"`

**API startup fails with "Port 5000 already in use"**
- Kill existing process: `lsof -ti:5000 | xargs kill -9` (macOS/Linux)
- Or use: `python rag/api.py PORT=5001`
