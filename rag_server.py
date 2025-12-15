"""
RAG Chatbot FastAPI Server

Dual-mode RAG system:
  - Normal RAG: question → Gemini embed → Qdrant search → context → Gemini → response
  - Selected Text: question + selectedText → skip Qdrant → Gemini → response

Endpoints:
  - POST /api/query
  - GET /api/health
"""

import os
import time
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import google.generativeai as genai
from qdrant_client import QdrantClient

# ---------------------------------------------------------------------------
# Environment & Config
# ---------------------------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "robotics_textbook_chunks")

TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required")

genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Chatbot API",
    description="AI Robotics Textbook RAG Assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Qdrant Client (lazy)
# ---------------------------------------------------------------------------

_qdrant: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        if not QDRANT_URL or not QDRANT_API_KEY:
            raise HTTPException(503, "Qdrant not configured")
        _qdrant = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60,
            prefer_grpc=False,
        )
    return _qdrant

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    selectedText: Optional[str] = None

class Source(BaseModel):
    source: str
    chunk_text: str
    score: float
    section: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    mode: str
    sources: List[Source]
    response_time_ms: int

class HealthResponse(BaseModel):
    status: str
    qdrant_connected: bool
    gemini_configured: bool
    collection_name: str
    collection_points: Optional[int] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def embed_query(text: str) -> List[float]:
    """
    Uses Gemini embedding API (768-dim).
    ZERO local memory usage.
    """
    try:
        res = genai.embed_content(
            model="models/embedding-001",
            content=text,
        )
        return res["embedding"]
    except Exception as e:
        raise HTTPException(500, f"Embedding failed: {e}")

async def search_qdrant(vector: List[float]) -> List[dict]:
    try:
        client = get_qdrant_client()
        result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=TOP_K,
            with_payload=True,
            with_vectors=False,
        )

        hits = []
        for p in result.points:
            payload = p.payload or {}
            hits.append({
                "text": payload.get("text", ""),
                "source": payload.get("source", "unknown"),
                "section": payload.get("section"),
                "score": p.score,
            })
        return hits

    except Exception as e:
        raise HTTPException(503, f"Qdrant search failed: {e}")

async def generate_answer(question: str, context: str, mode: str) -> str:
    try:
        prompt = (
            f"You are an AI assistant for an AI Robotics textbook.\n\n"
            f"{'Highlighted Text:' if mode == 'selected_text' else 'Context:'}\n"
            f"{context}\n\n"
            f"Question:\n{question}\n\nAnswer clearly and concisely:"
        )

        if len(prompt) > MAX_CONTEXT_LENGTH:
            prompt = prompt[:MAX_CONTEXT_LENGTH]

        model = genai.GenerativeModel("models/gemini-2.5-flash")
        resp = model.generate_content(prompt)

        if not resp or not resp.text:
            raise Exception("Empty Gemini response")

        return resp.text.strip()

    except Exception as e:
        if "429" in str(e):
            raise HTTPException(429, "Gemini rate limit exceeded")
        raise HTTPException(500, f"Gemini error: {e}")

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/query", response_model=QueryResponse)
async def query_api(req: QueryRequest):
    start = time.time()

    if req.selectedText and req.selectedText.strip():
        mode = "selected_text"
        context = req.selectedText.strip()
        sources = []
        answer = await generate_answer(req.question, context, mode)

    else:
        mode = "normal_rag"
        embedding = await embed_query(req.question)
        results = await search_qdrant(embedding)

        if not results:
            raise HTTPException(404, "No relevant content found")

        context_blocks = []
        sources = []

        for r in results:
            context_blocks.append(
                f"[{r['source']} - {r.get('section','')}]\n{r['text']}"
            )
            sources.append(Source(
                source=r["source"],
                chunk_text=r["text"][:200],
                score=round(r["score"], 3),
                section=r.get("section"),
            ))

        context = "\n\n".join(context_blocks)
        answer = await generate_answer(req.question, context, mode)

    return QueryResponse(
        answer=answer,
        mode=mode,
        sources=sources,
        response_time_ms=int((time.time() - start) * 1000),
    )

@app.get("/api/health", response_model=HealthResponse)
async def health():
    qdrant_ok = False
    points = None

    try:
        client = get_qdrant_client()
        info = client.get_collection(COLLECTION_NAME)
        qdrant_ok = True
        points = info.points_count
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if qdrant_ok else "degraded",
        qdrant_connected=qdrant_ok,
        gemini_configured=bool(GEMINI_API_KEY),
        collection_name=COLLECTION_NAME,
        collection_points=points,
    )

@app.get("/")
async def root():
    return {
        "service": "RAG Chatbot API",
        "endpoints": ["/api/query", "/api/health"],
    }
