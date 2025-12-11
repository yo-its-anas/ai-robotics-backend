# RAG Chatbot Integration Guide

This guide explains how to integrate the RAG chatbot into your Docusaurus site.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Frontend Integration](#frontend-integration)
3. [Backend Deployment](#backend-deployment)
4. [Configuration](#configuration)
5. [Testing Integration](#testing-integration)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before integrating the chatbot, ensure you have:

- ✅ Node.js 18+ installed
- ✅ Python 3.9+ installed (for backend)
- ✅ Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- ✅ Qdrant Cloud account ([Sign up here](https://cloud.qdrant.io/))
- ✅ Vercel account ([Sign up here](https://vercel.com/signup))

## Frontend Integration

### Step 1: Install ChatKit Dependencies

Add the ChatKit SDK to your Docusaurus project:

```bash
npm install @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles
```

### Step 2: Add Global Styles

Edit `docusaurus.config.js` to include the global ChatKit styles:

```javascript
module.exports = {
  // ... other config
  stylesheets: [
    '/ragchat.css',  // Add this line
  ],
  // ... rest of config
};
```

### Step 3: Add Chatbot to a Page

#### Option A: Add to a Specific Page

Create or edit a page (e.g., `src/pages/chat.js`):

```jsx
import React from 'react';
import Layout from '@theme/Layout';
import RagChat from '@site/src/components/RagChat';

export default function ChatPage() {
  return (
    <Layout title="Ask Questions" description="AI-powered Q&A for the textbook">
      <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
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

#### Option B: Add as a Floating Widget (Global)

To make the chatbot available site-wide as a floating button, create a custom Root component:

1. Create `src/theme/Root.js`:

```jsx
import React, { useState } from 'react';
import RagChat from '@site/src/components/RagChat';

export default function Root({ children }) {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <>
      {children}

      {/* Floating chat button */}
      <button
        onClick={() => setIsChatOpen(!isChatOpen)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          cursor: 'pointer',
          fontSize: '24px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 9999,
        }}
        aria-label="Toggle chat"
      >
        💬
      </button>

      {/* Floating chat panel */}
      {isChatOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px',
            right: '20px',
            width: '400px',
            height: '600px',
            zIndex: 9999,
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
            borderRadius: '12px',
            overflow: 'hidden',
          }}
        >
          <div style={{ position: 'relative', height: '100%' }}>
            <button
              onClick={() => setIsChatOpen(false)}
              style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                zIndex: 10000,
                background: 'rgba(0,0,0,0.5)',
                color: 'white',
                border: 'none',
                borderRadius: '50%',
                width: '30px',
                height: '30px',
                cursor: 'pointer',
                fontSize: '18px',
              }}
              aria-label="Close chat"
            >
              ×
            </button>
            <RagChat />
          </div>
        </div>
      )}
    </>
  );
}
```

#### Option C: Add to Navbar

Edit `docusaurus.config.js`:

```javascript
module.exports = {
  themeConfig: {
    navbar: {
      items: [
        // ... other items
        {
          to: '/chat',
          label: '💬 Ask AI',
          position: 'right',
        },
      ],
    },
  },
};
```

Then create `/src/pages/chat.js` as shown in Option A.

### Step 4: Update Backend URL

Edit `src/components/RagChat/config.js`:

```javascript
export const BACKEND_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://YOUR-VERCEL-APP.vercel.app';  // ⬅️ UPDATE THIS
```

Replace `YOUR-VERCEL-APP` with your actual Vercel deployment URL (see Backend Deployment section).

## Backend Deployment

### Step 1: Run Ingestion (One-Time)

Before deploying the backend, you need to populate Qdrant with your textbook content:

```bash
# 1. Set up environment
cd rag
cp config.env.example .env
# Edit .env with your API keys

# 2. Install Python dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run ingestion
python ingest.py --docs-dir ../docs --force
```

This will:
- Read all markdown files from `/docs`
- Chunk them into 500-token pieces
- Generate embeddings with Gemini
- Upload to Qdrant

**Expected output:**
```
✅ Created 342 chunks from 28 documents
✅ Generated embeddings for 342 chunks
✅ Successfully uploaded 342 chunks
```

### Step 2: Deploy Backend to Vercel

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy from /rag directory
cd rag
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? (select your account)
# - Link to existing project? No
# - Project name? rag-chatbot-backend (or your choice)
# - In which directory is your code? ./
# - Want to override settings? No

# 4. Set environment variables
vercel env add GEMINI_API_KEY
# Paste your Gemini API key

vercel env add QDRANT_URL
# Paste your Qdrant cluster URL (e.g., https://xyz.qdrant.io)

vercel env add QDRANT_API_KEY
# Paste your Qdrant API key

# 5. Deploy to production
vercel --prod
```

**Copy the production URL** (e.g., `https://rag-chatbot-backend.vercel.app`) and update it in `src/components/RagChat/config.js`.

### Step 3: Verify Backend Deployment

Test the deployed backend:

```bash
# Health check
curl https://YOUR-VERCEL-APP.vercel.app/api/health

# Test query
curl -X POST https://YOUR-VERCEL-APP.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SLAM?"}'
```

## Configuration

### Environment Variables

**Backend (.env in /rag):**
```env
GEMINI_API_KEY=your_key_here
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key_here
QDRANT_COLLECTION_NAME=robotics_textbook_chunks
TOP_K_RESULTS=5
CORS_ORIGINS=http://localhost:3000,https://your-site.github.io
```

**Frontend (config.js):**
```javascript
export const BACKEND_URL = 'https://YOUR-VERCEL-APP.vercel.app';
export const CHATBOT_CONFIG = {
  welcomeMessage: "Hi! I'm your AI assistant...",
  enableSelectedTextMode: true,
  maxMessageLength: 1000,
};
```

### Customization Options

#### Change Chatbot Appearance

Edit `src/components/RagChat/styles.module.css`:

```css
/* Change chat container height */
.chatContainer {
  height: 800px;  /* Default: 600px */
}

/* Change message bubble colors */
.cs-message--incoming .cs-message__content {
  background: #e3f2fd;  /* Customize this */
}
```

#### Change Welcome Message

Edit `src/components/RagChat/config.js`:

```javascript
export const CHATBOT_CONFIG = {
  welcomeMessage: "Welcome! Ask me anything about robotics!",
};
```

#### Adjust Search Results

Edit backend `.env`:

```env
TOP_K_RESULTS=10  # Default: 5 (more results = better context, slower)
```

## Testing Integration

### Local Testing

1. **Start backend locally:**
   ```bash
   cd rag
   source venv/bin/activate
   uvicorn rag_server:app --reload --port 8000
   ```

2. **Start frontend locally:**
   ```bash
   npm start
   ```

3. **Test both modes:**
   - Navigate to `/chat` (or wherever you added the component)
   - **Normal RAG**: Type "What is SLAM?" and submit
   - **Selected Text**: Highlight some text, then ask "Explain this"

### Production Testing

After deploying:

1. **Visit your deployed site**
2. **Test Normal RAG mode:**
   - Ask: "What are the main components of a robot?"
   - Verify: Response includes sources from textbook
3. **Test Selected Text mode:**
   - Highlight any paragraph on a textbook page
   - Ask: "Summarize this"
   - Verify: Response explains the highlighted text

## Troubleshooting

### Frontend Issues

**Problem:** "Module not found: @chatscope/chat-ui-kit-react"
- **Solution:** Run `npm install @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles`

**Problem:** Chatbot UI looks broken
- **Solution:** Ensure `/ragchat.css` is added to `docusaurus.config.js` stylesheets

**Problem:** "Network error" when sending messages
- **Solution:** Check that BACKEND_URL in config.js matches your Vercel deployment URL

### Backend Issues

**Problem:** "Qdrant connection failed"
- **Solution:** Verify QDRANT_URL and QDRANT_API_KEY in Vercel environment variables

**Problem:** "No relevant content found"
- **Solution:** Ensure ingestion completed successfully and Qdrant collection has points

**Problem:** CORS error in browser console
- **Solution:** Add your frontend URL to CORS_ORIGINS environment variable

### Deployment Issues

**Problem:** Vercel build fails
- **Solution:** Ensure `vercel.json` is present in /rag directory with correct Python configuration

**Problem:** "Environment variable not found" on Vercel
- **Solution:** Run `vercel env add <VAR_NAME>` for each required variable

## Support

For issues or questions:
- Check the [main README](/rag/README.md)
- Review [API documentation](/rag/docs/API.md)
- Open an issue on GitHub

## Next Steps

After successful integration:

1. ✅ Monitor usage in Vercel logs
2. ✅ Monitor Qdrant dashboard for performance
3. ✅ Adjust TOP_K_RESULTS based on answer quality
4. ✅ Customize UI to match your site's design
5. ✅ Add analytics to track chatbot usage
