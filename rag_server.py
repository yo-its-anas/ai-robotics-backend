"""
RAG Chatbot FastAPI Server

Dual-mode RAG system:
  - Normal RAG: question → embed → Qdrant search → context → Gemini → response
  - Selected Text: question + selectedText → skip Qdrant → Gemini → response

Endpoints:
  - POST /api/query: Main RAG endpoint
  - GET /api/health: Health check

Usage:
    uvicorn rag_server:app --reload --port 8000
"""

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

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "robotics_textbook_chunks")
TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    description="Dual-mode RAG system for AI Robotics textbook",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini for text generation
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize Sentence Transformer model (lazy loading)
embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy initialization of embedding model."""
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer('all-mpnet-base-v2')
    return embedding_model


# Initialize Qdrant (lazy connection)
qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Lazy initialization of Qdrant client."""
    global qdrant_client
    if qdrant_client is None:
        if not QDRANT_URL or not QDRANT_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Qdrant not configured. Set QDRANT_URL and QDRANT_API_KEY."
            )
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60, prefer_grpc=False)
    return qdrant_client


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for /api/query endpoint."""
    question: str = Field(..., min_length=1, description="User's question")
    selectedText: Optional[str] = Field(None, description="Optional highlighted text for focused explanation")


class Source(BaseModel):
    """Source document metadata."""
    source: str = Field(..., description="File path of source document")
    chunk_text: str = Field(..., description="Relevant text chunk")
    score: float = Field(..., description="Relevance score (0-1)")
    section: Optional[str] = Field(None, description="Section heading")


class QueryResponse(BaseModel):
    """Response model for /api/query endpoint."""
    answer: str = Field(..., description="Generated answer")
    mode: str = Field(..., description="RAG mode used: 'normal_rag' or 'selected_text'")
    sources: List[Source] = Field(default_factory=list, description="Source documents (empty for selected_text mode)")
    response_time_ms: int = Field(..., description="Response time in milliseconds")


class HealthResponse(BaseModel):
    """Response model for /api/health endpoint."""
    status: str
    qdrant_connected: bool
    gemini_configured: bool
    embedding_model_loaded: bool
    collection_name: str
    collection_points: Optional[int] = None


# ============================================================================
# Helper Functions
# ============================================================================

async def embed_query(query: str) -> List[float]:
    """
    Generate embedding for user query using Sentence Transformers.

    Args:
        query: User's question text

    Returns:
        768-dimensional embedding vector

    Raises:
        HTTPException: If embedding generation fails
    """
    try:
        model = get_embedding_model()
        embedding = model.encode(query, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate query embedding: {str(e)}"
        )


async def search_qdrant(embedding: List[float], top_k: int = TOP_K) -> List[dict]:
    """
    Search Qdrant for similar chunks.

    Args:
        embedding: Query embedding vector
        top_k: Number of results to return

    Returns:
        List of search results with text, metadata, and scores

    Raises:
        HTTPException: If Qdrant search fails
    """
    try:
        client = get_qdrant_client()
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k
        )

        results = []
        for hit in search_results:
            results.append({
                "text": hit.payload.get("text", ""),
                "source": hit.payload.get("source", "unknown"),
                "section": hit.payload.get("section"),
                "score": hit.score,
                "metadata": hit.payload
            })

        return results

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant search failed: {str(e)}"
        )


async def generate_response(question: str, context: str, mode: str = "normal_rag") -> str:
    """
    Generate answer using Gemini with context.

    Args:
        question: User's question
        context: Context text (from Qdrant or selectedText)
        mode: RAG mode ('normal_rag' or 'selected_text')

    Returns:
        Generated answer text

    Raises:
        HTTPException: If Gemini generation fails
    """
    try:
        if mode == "selected_text":
            # Selected Text mode: explain the highlighted text
            prompt = f"""You are an AI assistant helping students understand robotics concepts.

The student has highlighted the following text and asked a question about it:

**Highlighted Text:**
{context}

**Student's Question:**
{question}

Please provide a clear, focused explanation that directly addresses the student's question about the highlighted text. Use simple language and include examples where helpful.

Answer:"""
        else:
            # Normal RAG mode: answer using retrieved context
            prompt = f"""You are an AI assistant for an AI Robotics textbook. Answer the student's question using the context provided below.

**Context from Textbook:**
{context}

**Student's Question:**
{question}

Please provide a clear, accurate answer based on the context. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information is available. Use simple language appropriate for students learning robotics.

Answer:"""

        # Truncate context if too long
        if len(prompt) > MAX_CONTEXT_LENGTH:
            prompt = prompt[:MAX_CONTEXT_LENGTH] + "\n\n[Context truncated due to length...]"

        # Generate response using Gemini
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise Exception("Empty response from Gemini")

        return response.text.strip()

    except Exception as e:
        # Check for rate limiting
        if "429" in str(e) or "quota" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="API rate limit exceeded. Please try again in a moment."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Main RAG query endpoint with dual-mode logic.

    **Normal RAG Mode** (selectedText is empty/null):
      1. Embed the question
      2. Search Qdrant for relevant chunks
      3. Generate answer using retrieved context

    **Selected Text Mode** (selectedText provided):
      1. Skip Qdrant search
      2. Use selectedText directly as context
      3. Generate focused explanation

    Returns:
        QueryResponse with answer, mode, sources, and timing
    """
    start_time = time.time()

    # Validate question
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    try:
        # Determine mode based on selectedText presence
        if request.selectedText and request.selectedText.strip():
            # ============================================================
            # SELECTED TEXT MODE
            # ============================================================
            mode = "selected_text"
            context = request.selectedText.strip()
            sources = []

            # Generate response using selected text as context
            answer = await generate_response(request.question, context, mode="selected_text")

        else:
            # ============================================================
            # NORMAL RAG MODE
            # ============================================================
            mode = "normal_rag"

            # Step 1: Embed query
            query_embedding = await embed_query(request.question)

            # Step 2: Search Qdrant
            search_results = await search_qdrant(query_embedding, top_k=TOP_K)

            if not search_results:
                raise HTTPException(
                    status_code=404,
                    detail="No relevant content found in the textbook for your question."
                )

            # Step 3: Build context from top results
            context_parts = []
            sources = []

            for result in search_results:
                # Add to context
                source_label = result.get("source", "unknown").split("/")[-1]
                section_label = result.get("section", "")
                context_parts.append(
                    f"[Source: {source_label} - {section_label}]\n{result['text']}"
                )

                # Add to sources list
                sources.append(Source(
                    source=result["source"],
                    chunk_text=result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"],
                    score=round(result["score"], 3),
                    section=section_label if section_label else None
                ))

            context = "\n\n".join(context_parts)

            # Step 4: Generate answer
            answer = await generate_response(request.question, context, mode="normal_rag")

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        return QueryResponse(
            answer=answer,
            mode=mode,
            sources=sources,
            response_time_ms=response_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and connectivity to dependencies.
    """
    qdrant_connected = False
    collection_points = None

    # Check Qdrant connection
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(COLLECTION_NAME)
        qdrant_connected = True
        collection_points = collection_info.points_count
    except Exception:
        pass

    # Check Gemini configuration
    gemini_configured = GEMINI_API_KEY is not None

    # Check embedding model
    embedding_model_loaded = False
    try:
        get_embedding_model()
        embedding_model_loaded = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if (qdrant_connected and gemini_configured and embedding_model_loaded) else "degraded",
        qdrant_connected=qdrant_connected,
        gemini_configured=gemini_configured,
        embedding_model_loaded=embedding_model_loaded,
        collection_name=COLLECTION_NAME,
        collection_points=collection_points
    )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "query": "POST /api/query",
            "health": "GET /api/health"
        },
        "docs": "/docs"
    }


# For Vercel serverless deployment
handler = app
