# RAG Chatbot Testing Guide

Comprehensive testing instructions for validating the RAG chatbot system.

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Backend Tests](#backend-tests)
3. [Frontend Tests](#frontend-tests)
4. [Integration Tests](#integration-tests)
5. [Performance Tests](#performance-tests)
6. [Constitution Compliance](#constitution-compliance)

## Testing Strategy

The RAG chatbot testing follows this hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│  Level 1: Component Tests                               │
│  - Ingestion pipeline validation                        │
│  - Qdrant search validation                             │
│  - Gemini API integration                               │
│  - ChatKit UI rendering                                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Level 2: Mode Tests                                    │
│  - Normal RAG mode (question → search → answer)         │
│  - Selected Text mode (question + text → answer)        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Level 3: Integration Tests                             │
│  - End-to-end user scenarios                            │
│  - Error handling paths                                 │
│  - Cross-browser compatibility                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Level 4: Performance Tests                             │
│  - Response time targets                                │
│  - Concurrent user handling                             │
│  - Rate limiting behavior                               │
└─────────────────────────────────────────────────────────┘
```

## Backend Tests

### Test 1: Ingestion Pipeline Validation

**Objective:** Verify documents are correctly ingested into Qdrant

**Steps:**

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag
source venv/bin/activate

# Run ingestion
python ingest.py --docs-dir ../docs --force
```

**Expected Results:**

- ✅ No errors during document reading
- ✅ Chunks created: 300+ (depends on textbook size)
- ✅ Embeddings generated for all chunks
- ✅ All chunks uploaded to Qdrant
- ✅ Collection points count matches chunk count

**Validation Checks:**

```python
# In Python REPL:
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Check collection exists
collections = client.get_collections()
print(f"Collections: {[c.name for c in collections.collections]}")
# Expected: ['robotics_textbook_chunks']

# Check points count
info = client.get_collection("robotics_textbook_chunks")
print(f"Points: {info.points_count}")
# Expected: 300+ points

# Check vector dimensions
print(f"Vector size: {info.config.params.vectors.size}")
# Expected: 768

# Sample a point
points = client.scroll(
    collection_name="robotics_textbook_chunks",
    limit=1
)
print(f"Sample point payload: {points[0][0].payload}")
# Expected: Contains 'text', 'source', 'section', etc.
```

### Test 2: Qdrant Search Validation

**Objective:** Verify semantic search returns relevant results

**Test Script:**

```python
# test_qdrant_search.py
import google.generativeai as genai
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Test queries
test_queries = [
    "What is SLAM?",
    "How do robots navigate?",
    "Explain path planning algorithms",
]

for query in test_queries:
    print(f"\n🔍 Query: {query}")

    # Generate embedding
    result = genai.embed_content(
        model="models/embedding-001",
        content=query,
        task_type="retrieval_query"
    )
    embedding = result['embedding']

    # Search Qdrant
    search_results = client.search(
        collection_name="robotics_textbook_chunks",
        query_vector=embedding,
        limit=5
    )

    # Print results
    for i, hit in enumerate(search_results):
        print(f"  [{i+1}] Score: {hit.score:.3f} | Source: {hit.payload['source']}")
        print(f"      Preview: {hit.payload['text'][:100]}...")

    # Validation
    assert len(search_results) > 0, "No results found"
    assert search_results[0].score > 0.5, "Top result score too low"
    print("  ✅ PASS")
```

**Run test:**

```bash
python test_qdrant_search.py
```

**Expected Results:**

- ✅ All test queries return results
- ✅ Top result score > 0.5 (relevance threshold)
- ✅ Results contain textbook content related to query

### Test 3: FastAPI Endpoint Validation

**Objective:** Verify both modes work correctly

**Test Normal RAG Mode:**

```bash
# Test query endpoint
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is SLAM?"
  }' | jq
```

**Expected Response:**

```json
{
  "answer": "SLAM (Simultaneous Localization and Mapping) is...",
  "mode": "normal_rag",
  "sources": [
    {
      "source": "docs/chapter-3.md",
      "chunk_text": "SLAM is a technique...",
      "score": 0.876,
      "section": "Localization"
    }
  ],
  "response_time_ms": 2340
}
```

**Validation Checks:**

- ✅ `mode` === "normal_rag"
- ✅ `answer` is non-empty and relevant
- ✅ `sources` array has 3-5 items
- ✅ `response_time_ms` < 5000 (5 seconds)

**Test Selected Text Mode:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Explain this concept",
    "selectedText": "Kalman filters are used to estimate the state of a system from noisy observations..."
  }' | jq
```

**Expected Response:**

```json
{
  "answer": "This passage explains how Kalman filters work...",
  "mode": "selected_text",
  "sources": [],
  "response_time_ms": 1850
}
```

**Validation Checks:**

- ✅ `mode` === "selected_text"
- ✅ `answer` references the selected text
- ✅ `sources` array is empty
- ✅ `response_time_ms` < 3000 (faster than normal RAG)

### Test 4: Error Handling Validation

**Test empty question:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": ""}' | jq
```

**Expected:** HTTP 400 with error message

**Test invalid request:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"invalid": "field"}' | jq
```

**Expected:** HTTP 422 validation error

### Test 5: Health Check Validation

```bash
curl http://localhost:8000/api/health | jq
```

**Expected Response:**

```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "gemini_configured": true,
  "collection_name": "robotics_textbook_chunks",
  "collection_points": 342
}
```

## Frontend Tests

### Test 6: ChatKit UI Rendering

**Objective:** Verify chatbot UI renders correctly

**Steps:**

1. Start Docusaurus dev server: `npm start`
2. Navigate to `/chat` page
3. Observe UI elements

**Expected Results:**

- ✅ Chat container visible (600px height)
- ✅ Welcome message displayed
- ✅ Message input box present
- ✅ Placeholder text: "Ask a question about robotics..."
- ✅ Send button visible
- ✅ No console errors

### Test 7: Message Flow Validation

**Objective:** Verify messages are sent and received correctly

**Test Case 1: Send a message**

1. Type "What is SLAM?" in input box
2. Click Send or press Enter

**Expected Results:**

- ✅ User message appears in chat (right side, blue background)
- ✅ Typing indicator appears ("Bot is thinking...")
- ✅ Bot response appears within 5 seconds (left side, light blue)
- ✅ Response includes relevant content about SLAM
- ✅ Sources section visible with 3-5 sources

**Test Case 2: Error handling**

1. Disconnect network (simulate offline)
2. Send a message

**Expected Results:**

- ✅ Error message appears: "⚠️ Network error. Please check your connection..."
- ✅ Error message styled differently (yellow background)

### Test 8: Text Selection Handler Validation

**Objective:** Verify text selection feature works

**Steps:**

1. Navigate to any textbook page
2. Highlight a paragraph
3. Open chatbot (if floating widget) or navigate to `/chat`
4. Observe input placeholder

**Expected Results:**

- ✅ Placeholder updates to: "💡 Ask about the selected text..."
- ✅ Selection hint bubble appears (bottom-right)
- ✅ Hint shows preview: "💡 Text Selected: [preview]..."

**Test Case: Use selected text**

1. With text selected, type "Explain this"
2. Send message

**Expected Results:**

- ✅ Bot response explains the selected text (not general question)
- ✅ Mode indicator shows: "💡 Explaining selected text"
- ✅ No sources section (selected text mode doesn't use search)

## Integration Tests

### Test 9: End-to-End Normal RAG Scenario

**User Story:** Student wants to understand SLAM

**Steps:**

1. Open `/chat` page
2. Type: "What is SLAM and why is it important for robots?"
3. Wait for response
4. Click on a source link (if clickable)

**Expected Behavior:**

| Step | Expected Result | Status |
|------|----------------|--------|
| Page load | Chatbot UI renders, welcome message shown | ✅ |
| Type question | Input updates, character count valid | ✅ |
| Send message | User message appears, typing indicator shows | ✅ |
| Wait 3-5s | Bot response appears with relevant SLAM explanation | ✅ |
| Check sources | 3-5 sources listed with file names and scores | ✅ |
| Check response time | Response metadata shows < 5000ms | ✅ |

### Test 10: End-to-End Selected Text Scenario

**User Story:** Student highlights confusing text and asks for clarification

**Steps:**

1. Navigate to textbook page with complex content
2. Highlight paragraph about "Kalman filters"
3. Open chatbot
4. Type: "Simplify this for me"
5. Send message

**Expected Behavior:**

| Step | Expected Result | Status |
|------|----------------|--------|
| Highlight text | Selection hint appears | ✅ |
| Open chatbot | Placeholder shows selected text preview | ✅ |
| Send question | Selected text sent to backend as context | ✅ |
| Bot response | Explanation focuses on highlighted text only | ✅ |
| Mode indicator | Shows "Explaining selected text" | ✅ |
| Sources | Empty (no search performed) | ✅ |
| Response time | Faster than normal RAG (< 3000ms) | ✅ |

### Test 11: Error Recovery Scenario

**User Story:** System handles errors gracefully

**Test Case 1: Backend down**

1. Stop backend server (`Ctrl+C` on uvicorn)
2. Send a question in frontend

**Expected:** Error message: "Network error. Please check your connection..."

**Test Case 2: Rate limit exceeded**

1. Send 65+ questions rapidly (exceeds 60/min free tier)
2. Observe response on 61st request

**Expected:** Error message: "Too many requests. Please wait a moment..."

**Test Case 3: No relevant results**

1. Ask: "What is quantum entanglement?" (not in robotics textbook)
2. Observe response

**Expected:** Bot response acknowledges lack of information in textbook

## Performance Tests

### Test 12: Response Time Validation

**Objective:** Verify response times meet targets

**Test Script:**

```python
# test_performance.py
import requests
import time
import statistics

BACKEND_URL = "http://localhost:8000"
TEST_QUERIES = [
    {"question": "What is SLAM?"},
    {"question": "How do robots navigate?"},
    {"question": "Explain path planning"},
    {"question": "What are sensors used for?"},
    {"question": "Describe robot kinematics"},
]

response_times = []

for query in TEST_QUERIES:
    start = time.time()
    response = requests.post(f"{BACKEND_URL}/api/query", json=query)
    end = time.time()

    elapsed_ms = (end - start) * 1000
    response_times.append(elapsed_ms)

    print(f"Query: {query['question']}")
    print(f"  Response time: {elapsed_ms:.0f}ms")
    print(f"  Status: {response.status_code}")
    print()

print("=" * 50)
print(f"Average response time: {statistics.mean(response_times):.0f}ms")
print(f"Median response time: {statistics.median(response_times):.0f}ms")
print(f"Max response time: {max(response_times):.0f}ms")
print(f"Min response time: {min(response_times):.0f}ms")
print()

# Validation
assert statistics.mean(response_times) < 5000, "Average response time exceeds 5s"
assert max(response_times) < 10000, "Max response time exceeds 10s"
print("✅ Performance test PASSED")
```

**Target Metrics:**

| Metric | Target | Acceptable |
|--------|--------|------------|
| Normal RAG avg | < 3s | < 5s |
| Selected Text avg | < 2s | < 3s |
| P95 response time | < 5s | < 8s |
| Max response time | < 8s | < 10s |

### Test 13: Concurrent User Handling

**Objective:** Verify system handles multiple concurrent requests

**Test Script:**

```python
# test_concurrent.py
import requests
import concurrent.futures
import time

BACKEND_URL = "http://localhost:8000"
NUM_CONCURRENT_USERS = 10

def send_query(user_id):
    start = time.time()
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/query",
            json={"question": f"What is SLAM? (User {user_id})"},
            timeout=30
        )
        elapsed = time.time() - start
        return {
            "user_id": user_id,
            "status": response.status_code,
            "time": elapsed,
            "success": response.ok
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "status": 0,
            "time": time.time() - start,
            "success": False,
            "error": str(e)
        }

# Run concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CONCURRENT_USERS) as executor:
    results = list(executor.map(send_query, range(NUM_CONCURRENT_USERS)))

# Analyze results
successful = sum(1 for r in results if r["success"])
failed = NUM_CONCURRENT_USERS - successful
avg_time = sum(r["time"] for r in results) / len(results)

print(f"Concurrent users: {NUM_CONCURRENT_USERS}")
print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Average response time: {avg_time:.2f}s")
print()

assert successful >= NUM_CONCURRENT_USERS * 0.9, "More than 10% requests failed"
print("✅ Concurrent test PASSED")
```

**Target:** 90%+ success rate with 10-100 concurrent users

## Constitution Compliance

### Test 14: Isolation Validation

**Objective:** Verify RAG code doesn't modify textbook content

**Checks:**

```bash
# 1. Check no files created in /docs
ls -la /home/anaslinux/hackathon_q4/ai_robotics_book/docs/

# Expected: Only existing textbook files, no .pyc, .log, etc.

# 2. Check all RAG files in /rag
ls -la /home/anaslinux/hackathon_q4/ai_robotics_book/rag/

# Expected: Only ingest.py, rag_server.py, requirements.txt, etc.

# 3. Check frontend components isolated
ls -la /home/anaslinux/hackathon_q4/ai_robotics_book/src/components/RagChat/

# Expected: Only index.jsx, ChatKitWrapper.jsx, config.js, etc.

# 4. Verify no modifications to existing Docusaurus components
git status
git diff

# Expected: Only new files added, no modifications to existing textbook files
```

**Validation:**

- ✅ All backend code in `/rag/`
- ✅ All frontend code in `/src/components/RagChat/` and `/static/ragchat.css`
- ✅ No modifications to `/docs/` directory
- ✅ No modifications to existing Docusaurus theme or components (unless explicitly documented)

## Test Summary Checklist

Use this checklist to track test completion:

### Backend Tests

- [ ] Test 1: Ingestion pipeline validation
- [ ] Test 2: Qdrant search validation
- [ ] Test 3: FastAPI endpoint validation (Normal RAG)
- [ ] Test 3: FastAPI endpoint validation (Selected Text)
- [ ] Test 4: Error handling validation
- [ ] Test 5: Health check validation

### Frontend Tests

- [ ] Test 6: ChatKit UI rendering
- [ ] Test 7: Message flow validation
- [ ] Test 8: Text selection handler validation

### Integration Tests

- [ ] Test 9: End-to-end Normal RAG scenario
- [ ] Test 10: End-to-end Selected Text scenario
- [ ] Test 11: Error recovery scenarios

### Performance Tests

- [ ] Test 12: Response time validation
- [ ] Test 13: Concurrent user handling

### Constitution Compliance

- [ ] Test 14: Isolation validation

## Automated Test Suite

For ongoing validation, consider creating a pytest suite:

```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Create test file
# tests/test_rag_system.py

# Run tests
pytest tests/ -v
```

## Continuous Monitoring

After deployment, monitor:

1. **Vercel Logs:** `vercel logs --follow`
2. **Qdrant Dashboard:** https://cloud.qdrant.io/
3. **Browser Console:** Check for frontend errors
4. **User Feedback:** Collect ratings on answer quality

## Reporting Issues

When reporting bugs, include:

- Test case that failed
- Expected vs actual behavior
- Error messages (backend logs, browser console)
- Environment (local/production, browser, etc.)
