# RAG Chatbot Deployment Guide

Complete deployment instructions for both backend and frontend components.

## Overview

The RAG chatbot consists of two deployable components:

1. **Backend**: Python FastAPI server → Deployed to **Vercel**
2. **Frontend**: React components → Integrated into **Docusaurus** site (GitHub Pages)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Docusaurus Site (GitHub Pages)                        │ │
│  │  - Static textbook content                             │ │
│  │  - RagChat React component                             │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────┬─────────────────────────────────────────────┘
                │ POST /api/query
                ↓
┌───────────────────────────────────────────────────────────────┐
│  Backend (Vercel Serverless)                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  FastAPI Server (rag_server.py)                          │ │
│  │  - Dual-mode RAG logic                                   │ │
│  │  - Gemini integration                                    │ │
│  │  - Qdrant search                                         │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────┬───────────────────────────┬───────────────────┘
                │                           │
                ↓                           ↓
    ┌─────────────────────┐     ┌─────────────────────┐
    │  Gemini API         │     │  Qdrant Cloud       │
    │  (Google)           │     │  (Vector DB)        │
    └─────────────────────┘     └─────────────────────┘
```

## Prerequisites

### Accounts Needed

1. **Vercel Account** (Free tier sufficient)
   - Sign up: https://vercel.com/signup
   - Used for: Backend deployment

2. **Gemini API Key** (Free tier: 60 requests/minute)
   - Get key: https://makersuite.google.com/app/apikey
   - Used for: Embeddings + Chat generation

3. **Qdrant Cloud** (Free tier: 1GB storage)
   - Sign up: https://cloud.qdrant.io/
   - Used for: Vector database

4. **GitHub Account** (Required for GitHub Pages)
   - Your repository should already be set up

### Local Setup

- Node.js 18+
- Python 3.9+
- Git

## Part 1: Backend Deployment to Vercel

### Step 1: Create Qdrant Cluster

1. Go to https://cloud.qdrant.io/
2. Sign in / Sign up
3. Click "Create Cluster"
   - Cluster name: `robotics-textbook`
   - Region: Choose nearest to your users
   - Plan: Free (1GB)
4. Click "Create"
5. **Save credentials:**
   - Cluster URL: `https://xyz-abc123.qdrant.io`
   - API Key: Click "API Keys" → "Create API Key" → Copy key

### Step 2: Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. **Save the API key** (you won't see it again)

### Step 3: Run Data Ingestion

Before deploying the backend, populate Qdrant with textbook content:

```bash
# 1. Navigate to /rag directory
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp config.env.example .env

# 5. Edit .env with your credentials
nano .env  # or use any text editor

# Add these values:
# GEMINI_API_KEY=your_gemini_key_here
# QDRANT_URL=https://your-cluster.qdrant.io
# QDRANT_API_KEY=your_qdrant_key_here

# 6. Run ingestion pipeline
python ingest.py --docs-dir ../docs --force
```

**Expected output:**
```
✅ Configuration validated
✅ Gemini API configured
✅ Qdrant connection established
✅ Collection created successfully
📄 Found 28 markdown files
✅ Created 342 chunks from 28 documents
✅ Generated embeddings for 342 chunks
✅ Successfully uploaded 342 chunks
🎉 Ingestion complete!
```

**Time estimate:** 5-10 minutes (depends on textbook size)

### Step 4: Test Backend Locally

```bash
# Start local server
uvicorn rag_server:app --reload --port 8000

# In another terminal, test endpoints:

# Health check
curl http://localhost:8000/api/health

# Normal RAG query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SLAM?"}'

# Selected Text query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain this", "selectedText": "SLAM stands for Simultaneous Localization and Mapping..."}'
```

If all tests pass, proceed to deployment.

### Step 5: Deploy to Vercel

```bash
# 1. Install Vercel CLI (if not already installed)
npm install -g vercel

# 2. Login to Vercel
vercel login
# Follow browser prompts to authenticate

# 3. Deploy backend (from /rag directory)
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag
vercel

# Answer prompts:
? Set up and deploy? [Y/n] Y
? Which scope? (select your account)
? Link to existing project? [y/N] N
? What's your project's name? rag-chatbot-backend
? In which directory is your code located? ./
? Want to modify these settings? [y/N] N

# Vercel will deploy and give you a preview URL
```

**Output:**
```
🔗 Preview: https://rag-chatbot-backend-abc123.vercel.app
```

### Step 6: Add Environment Variables to Vercel

```bash
# Add Gemini API key
vercel env add GEMINI_API_KEY
? What's the value of GEMINI_API_KEY? [hidden]
? Expose GEMINI_API_KEY to which Environments? Production, Preview, Development
✓ Added Environment Variable GEMINI_API_KEY

# Add Qdrant URL
vercel env add QDRANT_URL
? What's the value of QDRANT_URL? https://your-cluster.qdrant.io
? Expose QDRANT_URL to which Environments? Production, Preview, Development
✓ Added Environment Variable QDRANT_URL

# Add Qdrant API key
vercel env add QDRANT_API_KEY
? What's the value of QDRANT_API_KEY? [hidden]
? Expose QDRANT_API_KEY to which Environments? Production, Preview, Development
✓ Added Environment Variable QDRANT_API_KEY
```

### Step 7: Deploy to Production

```bash
vercel --prod
```

**Output:**
```
🎉 Production: https://rag-chatbot-backend.vercel.app
```

**Save this URL!** You'll need it for frontend configuration.

### Step 8: Verify Production Deployment

```bash
# Health check
curl https://rag-chatbot-backend.vercel.app/api/health

# Expected response:
{
  "status": "healthy",
  "qdrant_connected": true,
  "gemini_configured": true,
  "collection_name": "robotics_textbook_chunks",
  "collection_points": 342
}

# Test query
curl -X POST https://rag-chatbot-backend.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SLAM?"}'

# Expected response:
{
  "answer": "SLAM (Simultaneous Localization and Mapping) is...",
  "mode": "normal_rag",
  "sources": [...],
  "response_time_ms": 2340
}
```

✅ **Backend deployment complete!**

## Part 2: Frontend Integration

### Step 1: Install Frontend Dependencies

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book

# Install ChatKit SDK
npm install @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles
```

### Step 2: Update Backend URL

Edit `src/components/RagChat/config.js`:

```javascript
export const BACKEND_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://rag-chatbot-backend.vercel.app';  // ⬅️ UPDATE THIS LINE
```

Replace with your actual Vercel production URL from Step 7.

### Step 3: Add Global Styles

Edit `docusaurus.config.js`:

```javascript
module.exports = {
  // ... existing config

  stylesheets: [
    '/ragchat.css',  // Add this line
  ],

  // ... rest of config
};
```

### Step 4: Create Chat Page

Create `src/pages/chat.js`:

```jsx
import React from 'react';
import Layout from '@theme/Layout';
import RagChat from '@site/src/components/RagChat';

export default function ChatPage() {
  return (
    <Layout
      title="AI Assistant"
      description="Ask questions about the AI Robotics textbook"
    >
      <div style={{
        padding: '2rem',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <h1>Ask the AI Assistant</h1>
        <p>
          Ask questions about the textbook, or highlight text on any page
          and ask for an explanation!
        </p>
        <RagChat />
      </div>
    </Layout>
  );
}
```

### Step 5: Add to Navigation (Optional)

Edit `docusaurus.config.js`:

```javascript
module.exports = {
  themeConfig: {
    navbar: {
      items: [
        // ... existing items
        {
          to: '/chat',
          label: '💬 AI Assistant',
          position: 'right',
        },
      ],
    },
  },
};
```

### Step 6: Test Locally

```bash
# Start Docusaurus dev server
npm start

# Visit: http://localhost:3000/chat
```

Test both modes:
1. **Normal RAG**: Ask "What is SLAM?"
2. **Selected Text**: Highlight text on any page, then ask "Explain this"

### Step 7: Deploy to GitHub Pages

```bash
# Build the site
npm run build

# Deploy to GitHub Pages
GIT_USER=anaslinux npm run deploy
```

**Expected output:**
```
✓ Website built successfully
✓ Deployed to GitHub Pages
🌐 https://anaslinux.github.io/ai_robotics_book/
```

### Step 8: Verify Production Frontend

1. Visit your deployed site: https://anaslinux.github.io/ai_robotics_book/chat
2. Test Normal RAG mode
3. Test Selected Text mode
4. Check browser console for errors (should be none)

✅ **Frontend deployment complete!**

## Part 3: Post-Deployment Configuration

### Update CORS Origins

The backend needs to allow requests from your GitHub Pages domain:

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag

# Add CORS_ORIGINS environment variable
vercel env add CORS_ORIGINS

? What's the value of CORS_ORIGINS? https://anaslinux.github.io
? Expose CORS_ORIGINS to which Environments? Production

# Redeploy to apply changes
vercel --prod
```

### Monitor Backend Performance

View Vercel deployment logs:

```bash
vercel logs rag-chatbot-backend --follow
```

Or visit: https://vercel.com/dashboard → Select project → Deployments

### Monitor Qdrant Usage

1. Go to https://cloud.qdrant.io/
2. Click your cluster
3. View dashboard:
   - Storage used
   - API requests
   - Collection stats

## Updating the System

### Re-run Ingestion (When Textbook Changes)

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag
source venv/bin/activate

# Re-ingest with --force to replace existing data
python ingest.py --docs-dir ../docs --force
```

### Update Backend Code

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book/rag

# Make changes to rag_server.py or other files

# Deploy updates
vercel --prod
```

### Update Frontend Code

```bash
cd /home/anaslinux/hackathon_q4/ai_robotics_book

# Make changes to src/components/RagChat/*

# Rebuild and deploy
npm run build
GIT_USER=anaslinux npm run deploy
```

## Troubleshooting

### Backend Issues

**Problem:** "Collection not found" error
```bash
# Solution: Re-run ingestion
cd rag
source venv/bin/activate
python ingest.py --docs-dir ../docs --force
```

**Problem:** "Gemini API quota exceeded"
```bash
# Solution: Wait 1 minute (free tier: 60 req/min)
# Or upgrade Gemini API quota in Google Cloud Console
```

**Problem:** Vercel deployment fails
```bash
# Solution: Check vercel.json is present and valid
cat vercel.json

# Ensure all dependencies are in requirements.txt
cat requirements.txt
```

### Frontend Issues

**Problem:** "Network error" in browser
```bash
# Solution: Check BACKEND_URL in config.js
# Ensure it matches your Vercel production URL
```

**Problem:** CORS error in browser console
```bash
# Solution: Add your GitHub Pages URL to CORS_ORIGINS
vercel env add CORS_ORIGINS
# Value: https://anaslinux.github.io
vercel --prod
```

## Cost Monitoring

All services used offer free tiers:

| Service | Free Tier | Usage Estimate |
|---------|-----------|----------------|
| **Vercel** | 100GB bandwidth, 100 serverless function invocations/day | ~1000 users/day |
| **Gemini API** | 60 requests/minute | ~100 users/day |
| **Qdrant Cloud** | 1GB storage | ~500 documents |
| **GitHub Pages** | Unlimited | ∞ |

**Recommendation:** Monitor usage in first week and adjust as needed.

## Security Checklist

- [x] API keys stored in Vercel environment variables (not in code)
- [x] CORS restricted to your domain only
- [x] `.env` files added to `.gitignore`
- [x] Qdrant API key kept secret
- [x] No sensitive data in frontend code

## Performance Optimization

### Backend

- **Cache frequently asked questions** (future enhancement)
- **Increase TOP_K_RESULTS** if answers lack context (but slower)
- **Decrease TOP_K_RESULTS** for faster responses (but less context)

### Frontend

- **Lazy load chatbot component** on user click (reduce initial page load)
- **Debounce message sends** to prevent spam
- **Show loading indicators** for better UX

## Next Steps

After deployment:

1. ✅ Share the chat page URL with users
2. ✅ Monitor Vercel logs for errors
3. ✅ Collect user feedback on answer quality
4. ✅ Adjust TOP_K_RESULTS based on feedback
5. ✅ Consider adding analytics (Google Analytics, Plausible, etc.)

## Support

- Vercel Issues: https://vercel.com/support
- Qdrant Docs: https://qdrant.tech/documentation/
- Gemini API Docs: https://ai.google.dev/docs
