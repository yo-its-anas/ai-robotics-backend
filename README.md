# RAG Chatbot Backend

This directory contains the backend implementation for the RAG (Retrieval-Augmented Generation) chatbot that provides intelligent Q&A for the AI Robotics textbook.

## Features

- **Dual-Mode RAG System**:
  - **Normal RAG Mode**: Semantic search across textbook using Qdrant + Gemini
  - **Selected Text Mode**: Direct explanation of highlighted text without search
- **Google Gemini Integration**: Embeddings (embedding-001) + Chat (gemini-pro)
- **Qdrant Vector Database**: Fast semantic search with HNSW indexing
- **FastAPI Backend**: High-performance async API with CORS support
- **Vercel Serverless**: Easy deployment with environment variable management

## Directory Structure

```
/rag/
├── ingest.py              # Document ingestion pipeline
├── rag_server.py          # FastAPI backend server
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── config.env.example    # Environment variable template
└── README.md             # This file
```

## Local Development Setup

### Prerequisites

- Python 3.9+
- Gemini API key (get from https://makersuite.google.com/app/apikey)
- Qdrant Cloud account (free tier at https://cloud.qdrant.io/)

### Installation

1. **Create virtual environment**:
   ```bash
   cd rag
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp config.env.example .env
   # Edit .env with your API keys
   ```

4. **Run ingestion** (first time only):
   ```bash
   python ingest.py --docs-dir ../docs --force
   ```

5. **Start local server**:
   ```bash
   uvicorn rag_server:app --reload --port 8000
   ```

6. **Test the API**:
   ```bash
   # Normal RAG mode
   curl -X POST http://localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What is SLAM?"}'

   # Selected Text mode
   curl -X POST http://localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"question": "Explain this", "selectedText": "Kalman filters..."}'
   ```

## Deployment to Vercel

### First-Time Setup

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Set environment variables**:
   ```bash
   cd rag
   vercel env add GEMINI_API_KEY
   vercel env add QDRANT_URL
   vercel env add QDRANT_API_KEY
   ```

4. **Deploy**:
   ```bash
   vercel --prod
   ```

### Updates

```bash
cd rag
vercel --prod
```

## API Documentation

### POST /api/query

**Request Body**:
```json
{
  "question": "What is SLAM?",
  "selectedText": "Optional highlighted text..."
}
```

**Response** (Normal RAG):
```json
{
  "answer": "SLAM stands for Simultaneous Localization and Mapping...",
  "mode": "normal_rag",
  "sources": [
    {
      "source": "docs/chapter-1.md",
      "chunk_text": "...",
      "score": 0.89
    }
  ],
  "response_time_ms": 1234
}
```

**Response** (Selected Text):
```json
{
  "answer": "This passage explains...",
  "mode": "selected_text",
  "sources": [],
  "response_time_ms": 856
}
```

### GET /api/health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "gemini_configured": true
}
```

## Configuration

See `config.env.example` for all available environment variables:

- **GEMINI_API_KEY**: Required for embeddings and chat
- **QDRANT_URL**: Qdrant cluster URL
- **QDRANT_API_KEY**: Qdrant authentication
- **TOP_K_RESULTS**: Number of search results (default: 5)
- **CHUNK_SIZE**: Token size for chunks (default: 500)

## Troubleshooting

### Ingestion Issues

**Problem**: "No documents found in /docs"
- **Solution**: Ensure `/docs` directory contains markdown files

**Problem**: "Qdrant connection failed"
- **Solution**: Verify QDRANT_URL and QDRANT_API_KEY in .env

### Server Issues

**Problem**: "CORS error from frontend"
- **Solution**: Add frontend URL to CORS_ORIGINS in .env

**Problem**: "Gemini API rate limit"
- **Solution**: Adjust BATCH_DELAY_SECONDS in .env (increase delay)

### Deployment Issues

**Problem**: "Environment variables not found on Vercel"
- **Solution**: Run `vercel env add` for each variable

**Problem**: "Build fails on Vercel"
- **Solution**: Ensure requirements.txt uses compatible versions

## Architecture

```
User Query
    ↓
[Frontend] → POST /api/query
    ↓
[rag_server.py]
    ├─ selectedText? → Skip search → Gemini
    └─ Normal mode → Embed query → Qdrant search → Gemini
         ↓
    Response with answer + sources
```

## Maintenance

### Re-ingesting Documents

When textbook content updates:

```bash
python ingest.py --docs-dir ../docs --force
```

### Monitoring

Check Vercel logs:
```bash
vercel logs
```

Check Qdrant dashboard:
https://cloud.qdrant.io/

## Performance

- **Normal RAG**: ~2-4s response time
- **Selected Text**: ~1-2s response time
- **Throughput**: 100+ concurrent users (free tier)
- **Search Accuracy**: ~90% relevance for top-5 results

## License

Same as parent project.

## Support

For issues, see: [Project Issues](https://github.com/anaslinux/ai_robotics_book/issues)
