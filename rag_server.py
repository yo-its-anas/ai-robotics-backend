"""
RAG Chatbot FastAPI Server (Render Free-Tier Safe)

Modes:
- Normal RAG: question → Qdrant (scroll fallback) → Gemini → response
- Selected Text: question + selectedText → Gemini → response

Endpoints:
- POST /api/query
- GET  /api/health
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

# ------------------------------------------------------------------
# ENV
# ------------------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "robotics_textbook_chunks")

TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ------------------------------------------------------------------
# APP
# ------------------------------------------------------------------

app = FastAPI(
    title="AI Robotics RAG API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# GEMINI
# ------------------------------------------------------------------

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required")

genai.configure(api_key=GEMINI_API_KEY)

# ------------------------------------------------------------------
# QDRANT (lazy)
# ------------------------------------------------------------------

_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        if not QDRANT_URL or not QDRANT_API_KEY:
            raise HTTPException(503, "Qdrant not configured")
        _qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30,
            prefer_grpc=False,
        )
    return _qdrant_client


# ------------------------------------------------------------------
# MODELS
# ------------------------------------------------------------------

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
    collection_points: Optional[int]


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

async def qdrant_fallback_search(limit: int = TOP_K) -> List[dict]:
    """
    Safe scroll-based retrieval (NO embeddings, NO memory spikes).
    """
    client = get_qdrant_client()
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=limit,
        with_payload=True,
    )

    results = []
    for p in points:
        payload = p.payload or {}
        results.append({
            "text": payload.get("text", ""),
            "source": payload.get("source", "unknown"),
            "section": payload.get("section"),
            "score": 1.0,
        })

    return results


def build_prompt(question: str, context: str, selected: bool) -> str:
    if selected:
        return f"""
You are an AI Robotics tutor.

Highlighted text:
{context}

Question:
{question}

Explain clearly in simple terms.
"""
    return f"""
You are an AI assistant for an AI Robotics textbook.

Context:
{context}

Question:
{question}

Answer clearly and concisely.
"""


async def generate_answer(prompt: str) -> str:
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(prompt)
    if not response or not response.text:
        raise HTTPException(500, "Empty response from Gemini")
    return response.text.strip()


# ------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    start = time.time()

    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    # ---------------- Selected Text Mode ----------------
    if request.selectedText and request.selectedText.strip():
        prompt = build_prompt(
            request.question,
            request.selectedText.strip(),
            selected=True,
        )
        answer = await generate_answer(prompt)

        return QueryResponse(
            answer=answer,
            mode="selected_text",
            sources=[],
            response_time_ms=int((time.time() - start) * 1000),
        )

    # ---------------- Normal RAG Mode ----------------
    docs = await qdrant_fallback_search()

    if not docs:
        raise HTTPException(404, "No content found")

    context = "\n\n".join(
        f"[{d['source']}]\n{d['text']}" for d in docs
    )

    if len(context) > MAX_CONTEXT_LENGTH:
        context = context[:MAX_CONTEXT_LENGTH]

    prompt = build_prompt(request.question, context, selected=False)
    answer = await generate_answer(prompt)

    sources = [
        Source(
            source=d["source"],
            chunk_text=d["text"][:200],
            score=d["score"],
            section=d.get("section"),
        )
        for d in docs
    ]

    return QueryResponse(
        answer=answer,
        mode="normal_rag",
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
        gemini_configured=True,
        collection_name=COLLECTION_NAME,
        collection_points=points,
    )


@app.get("/")
async def root():
    return {"service": "AI Robotics RAG API"}
