"""Simple Flask API for RAG retrieval with Claude generation."""
from flask import Flask, request, jsonify
from pathlib import Path
import json
import sys

try:
    from embed_and_index import retrieve
    import anthropic
except ImportError:
    print("Install: pip install flask anthropic")
    sys.exit(1)

app = Flask(__name__)

# Load index for article lookups
INDEX_PATH = Path(__file__).parent / 'index.json'
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    INDEX = json.load(f)

ARTICLES_BY_ID = {a['id']: a for a in INDEX['articles']}

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'ok'})

@app.route('/search', methods=['POST'])
def search():
    """Search corpus for similar chunks (embeddings-based)."""
    data = request.json
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    
    if not query:
        return jsonify({'error': 'query required'}), 400
    
    try:
        results = retrieve(query, top_k=top_k)
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    """Ask the corpus: retrieve + generate answer with Claude."""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'query required'}), 400
    
    try:
        # Retrieve similar chunks
        results = retrieve(query, top_k=3)
        
        if not results:
            return jsonify({
                'query': query,
                'answer': 'The corpus does not contain relevant information about this query.',
                'citations': []
            })
        
        # Build context from retrieved chunks
        context = "\n\n".join([
            f"Article {ARTICLES_BY_ID.get(r['article_id'], {}).get('title', 'Unknown')} (Chunk {r['chunk_id']}):\n{r['text']}"
            for r in results
        ])
        
        # Generate answer with Claude
        client = anthropic.Anthropic()
        response = client.messages.create(
            model='claude-3-5-sonnet-20241022',
            max_tokens=500,
            messages=[{
                'role': 'user',
                'content': f"""Based on the following excerpts from Babken Chookaszian's collected works, answer this question. 
Be concise and cite the original chunks.

CONTEXT:
{context}

QUESTION: {query}

Answer (cite chunk IDs in [brackets]):"""
            }]
        )
        
        answer = response.content[0].text
        
        return jsonify({
            'query': query,
            'answer': answer,
            'citations': [
                {
                    'article_id': r['article_id'],
                    'chunk_id': r['chunk_id'],
                    'similarity': r['similarity'],
                    'text': r['text'][:200]
                }
                for r in results
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("RAG API running on http://localhost:5000")
    print("POST /ask with {'query': '...'} to ask corpus")
    app.run(debug=True, port=5000)
