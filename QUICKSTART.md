# RAG Chatbot - Quick Start Guide

Get the RAG chatbot running in under 15 minutes!

## 🚀 Fast Track Setup

### Prerequisites (5 minutes)

1. **Get API Keys:**
   - Gemini: https://makersuite.google.com/app/apikey (Free)
   - Qdrant: https://cloud.qdrant.io/ (Create cluster, get API key)

2. **Install Dependencies:**
   ```bash
   # Python dependencies (for backend)
   cd rag
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt

   # Node dependencies (for frontend)
   cd ..
   npm install @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles
   ```

### Backend Setup (5 minutes)

```bash
cd rag

# 1. Configure environment
cp config.env.example .env
nano .env  # Add your API keys

# 2. Run ingestion (populate Qdrant with textbook content)
python ingest.py --docs-dir ../docs --force

# 3. Start local server
uvicorn rag_server:app --reload --port 8000
```

**Test backend:**
```bash
# In another terminal
curl http://localhost:8000/api/health
```

Expected: `{"status": "healthy", ...}`

### Frontend Setup (5 minutes)

```bash
cd ..  # Back to project root

# 1. Update docusaurus.config.js
# Add to stylesheets array:
#   stylesheets: ['/ragchat.css']

# 2. Start Docusaurus
npm start

# 3. Visit: http://localhost:3000/chat
```

**Test chatbot:**
- Type: "What is SLAM?"
- Highlight text on any page, ask: "Explain this"

---

## 📦 What's Included

### Backend Files (`/rag/`)

```
/rag/
├── ingest.py              # Document ingestion pipeline
├── rag_server.py          # FastAPI server (dual-mode RAG)
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── config.env.example    # Environment template
├── README.md             # Backend documentation
└── docs/
    ├── INTEGRATION.md    # Integration guide
    ├── DEPLOYMENT.md     # Deployment guide
    └── TESTING.md        # Testing guide
```

### Frontend Files (`/src/components/RagChat/`)

```
/src/components/RagChat/
├── index.jsx             # Main export
├── ChatKitWrapper.jsx    # ChatKit UI component
├── TextSelectionHandler.js # Text selection hook
├── config.js             # Backend URL config
└── styles.module.css     # Component styles

/static/
└── ragchat.css          # Global ChatKit styles
```

---

## 🎯 Key Features

### 1. Normal RAG Mode
```
User asks: "What is SLAM?"
  ↓ Embed question
  ↓ Search Qdrant
  ↓ Retrieve top 5 chunks
  ↓ Generate answer with Gemini
  ↓ Return answer + sources
```

### 2. Selected Text Mode
```
User highlights text + asks: "Explain this"
  ↓ Skip Qdrant search
  ↓ Use selected text as context
  ↓ Generate focused explanation
  ↓ Return answer (no sources)
```

---

## 🔧 Configuration

### Backend (`/rag/.env`)

```env
# Required
GEMINI_API_KEY=your_key_here
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key_here

# Optional (defaults shown)
QDRANT_COLLECTION_NAME=robotics_textbook_chunks
CHUNK_SIZE=500
CHUNK_OVERLAP=150
TOP_K_RESULTS=5
```

### Frontend (`/src/components/RagChat/config.js`)

```javascript
export const BACKEND_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://YOUR-VERCEL-APP.vercel.app';  // Update after deploying
```

---

## 🚢 Deployment (Quick)

### Deploy Backend to Vercel

```bash
cd rag

# 1. Install Vercel CLI
npm install -g vercel

# 2. Deploy
vercel

# 3. Add environment variables
vercel env add GEMINI_API_KEY
vercel env add QDRANT_URL
vercel env add QDRANT_API_KEY

# 4. Deploy to production
vercel --prod
```

**Copy the production URL** and update `config.js`.

### Deploy Frontend to GitHub Pages

```bash
cd ..  # Back to project root

# 1. Build
npm run build

# 2. Deploy
GIT_USER=anaslinux npm run deploy
```

---

## 🧪 Testing

### Quick Backend Test

```bash
# Normal RAG
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SLAM?"}'

# Selected Text
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain this", "selectedText": "SLAM is..."}'
```

### Quick Frontend Test

1. Visit `/chat`
2. Ask: "What is SLAM?"
3. Highlight text, ask: "Explain this"

---

## 🐛 Troubleshooting

### "No module named 'google.generativeai'"
```bash
pip install -r requirements.txt
```

### "CORS error" in browser
```bash
# Add your frontend URL to backend CORS_ORIGINS
echo 'CORS_ORIGINS=http://localhost:3000,https://your-site.github.io' >> .env
```

### "Collection not found"
```bash
# Re-run ingestion
python ingest.py --docs-dir ../docs --force
```

### "Network error" in chatbot
```bash
# Check BACKEND_URL in config.js matches running server
# Local: http://localhost:8000
# Production: https://your-vercel-app.vercel.app
```

---

## 📚 Next Steps

1. **Read full documentation:**
   - [Integration Guide](docs/INTEGRATION.md)
   - [Deployment Guide](docs/DEPLOYMENT.md)
   - [Testing Guide](docs/TESTING.md)

2. **Customize the chatbot:**
   - Edit welcome message in `config.js`
   - Adjust styles in `styles.module.css`
   - Modify TOP_K_RESULTS in backend `.env`

3. **Monitor performance:**
   - Vercel logs: `vercel logs --follow`
   - Qdrant dashboard: https://cloud.qdrant.io/

---

## 🆘 Support

- **Backend Issues:** See `/rag/README.md`
- **Frontend Issues:** See `/rag/docs/INTEGRATION.md`
- **Testing:** See `/rag/docs/TESTING.md`
- **Deployment:** See `/rag/docs/DEPLOYMENT.md`

---

## ✅ Success Criteria

You've successfully set up the RAG chatbot if:

- ✅ Backend health check returns `{"status": "healthy"}`
- ✅ Chatbot UI renders on `/chat` page
- ✅ Normal RAG mode returns relevant answers with sources
- ✅ Selected Text mode explains highlighted text
- ✅ No errors in browser console or server logs

**Congratulations! Your RAG chatbot is ready! 🎉**
