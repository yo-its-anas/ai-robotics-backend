import os
import time
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sentence_transformers import SentenceTransformer
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

TOP_K = 5
MAX_CONTEXT_LENGTH = 4000
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ------------------------------------------------------------------
# APP
# ------------------------------------------------------------------
app = FastAPI(title="RAG Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ------------------------------------------------------------------
# LAZY LOADERS (IMPORTANT)
# ------------------------------------------------------------------
_embedding_model: Optional[SentenceTransformer] = None
_qdrant_client: Optional[QdrantClient] = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embedding_model


def get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            prefer_grpc=False,
            timeout=60,
        )
    return _qdrant_client


# ------------------------------------------------------------------
# MODELS
# ------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str
    selectedText: Optional[str] = None


class Source(BaseModel):
    source: str
    chunk_text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    mode: str
    sources: List[Source]
    response_time_ms: int


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def embed(text: str) -> List[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()


def search_qdrant(vector: List[float]):
    client = get_qdrant()
    res = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=TOP_K,
        with_payload=True,
    )

    results = []
    for p in res.points:
        payload = p.payload or {}
        results.append({
            "text": payload.get("text", ""),
            "source": payload.get("source", "unknown"),
            "score": p.score,
        })

    return results


def generate_answer(question: str, context: str) -> str:
    prompt = f"""
You are an AI Robotics textbook assistant.

Context:
{context}

Question:
{question}

Answer clearly and concisely:
"""

    model = genai.GenerativeModel("models/gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


# ------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------
@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    start = time.time()

    if req.selectedText:
        answer = generate_answer(req.question, req.selectedText)
        return QueryResponse(
            answer=answer,
            mode="selected_text",
            sources=[],
            response_time_ms=int((time.time() - start) * 1000),
        )

    vector = embed(req.question)
    hits = search_qdrant(vector)

    if not hits:
        raise HTTPException(404, "No relevant content found")

    context = "\n\n".join(h["text"] for h in hits)
    answer = generate_answer(req.question, context)

    sources = [
        Source(
            source=h["source"],
            chunk_text=h["text"][:200],
            score=round(h["score"], 3),
        )
        for h in hits
    ]

    return QueryResponse(
        answer=answer,
        mode="normal_rag",
        sources=sources,
        response_time_ms=int((time.time() - start) * 1000),
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
