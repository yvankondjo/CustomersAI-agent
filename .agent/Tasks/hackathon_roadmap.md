# Hackathon Roadmap (12-Hour Sprint)

**Related docs:** [prd.md](./prd.md), [mvp_features.md](./mvp_features.md), [project_architecture.md](../System/project_architecture.md)

---

## 🎯 Objectif

Livrer un **MVP fonctionnel et déployable** en 12 heures avec une démo fluide.

**Règle d'or :** Un flow parfait, même minimal, bat 10 features à moitié finies.

---

## ⏱️ Time Allocation

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1** | 2.5h | Setup + Backend core |
| **Phase 2** | 2h | RAG pipeline |
| **Phase 3** | 2h | Frontend chat UI |
| **Phase 4** | 1.5h | Website ingestion |
| **Phase 5** | 1.5h | LangGraph router |
| **Phase 6** | 1.5h | Polish + démo prep |
| **Buffer** | 1h | Debug + imprévus |

---

## 🚀 Phase 1 : Setup + Backend Core (2.5h)

### 1.1 — Project Setup (30min)

**Backend:**
```bash
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn supabase qdrant-client openai langgraph langchain
```

**Create structure:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── nodes.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag.py
│   │   ├── embedding.py
│   │   └── supabase_client.py
│   └── models/
│       ├── __init__.py
│       └── schemas.py
├── requirements.txt
└── .env
```

**Frontend:**
```bash
npx create-next-app@latest frontend --typescript --tailwind --app
cd frontend
npm install @tanstack/react-query axios
```

**.env setup:**
```env
# Supabase
SUPABASE_URL=https://kttpamevcntespkhnijx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_api_key

# OpenAI (via OpenRouter)
OPENAI_API_KEY=your_openrouter_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# LLM Config
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
```

**✅ Checkpoint:**
- [ ] Folders created
- [ ] Dependencies installed
- [ ] .env configured

---

### 1.2 — Supabase Schema (45min)

**Use Supabase MCP to create tables:**

```sql
-- Create essential tables (tenants, conversations, messages, knowledge_chunks)
-- See: database_schema.md for full schema
```

**Priority tables for MVP:**
1. `tenants`
2. `conversations`
3. `conversation_messages`
4. `knowledge_chunks`
5. `website_pages` (if time)

**✅ Checkpoint:**
- [ ] Tables created in Supabase
- [ ] RLS policies enabled
- [ ] Test data inserted

---

### 1.3 — FastAPI Basic Routes (45min)

**`app/main.py`:**
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Customer AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    tenant_id: str
    user_id: str
    channel: str  # 'instagram', 'widget'
    content: str

class MessageResponse(BaseModel):
    response: str
    intent: str | None
    sources: list[str] | None

@app.post("/api/v1/support/message", response_model=MessageResponse)
async def handle_message(request: MessageRequest):
    """Main endpoint for all messages."""

    # TODO: Route to LangGraph
    # For now, simple echo
    return MessageResponse(
        response=f"Echo: {request.content}",
        intent="unknown",
        sources=None
    )

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Test:**
```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

**✅ Checkpoint:**
- [ ] FastAPI runs
- [ ] `/health` returns 200
- [ ] `/support/message` accepts requests

---

### 1.4 — Supabase Client (30min)

**`app/services/supabase_client.py`:**
```python
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

async def save_conversation(tenant_id: str, user_id: str, channel: str):
    """Get or create conversation."""
    result = supabase.table("conversations").select("*").eq(
        "tenant_id", tenant_id
    ).eq("user_id", user_id).eq("channel", channel).execute()

    if result.data:
        return result.data[0]

    # Create new
    new_conv = supabase.table("conversations").insert({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "channel": channel,
        "status": "open"
    }).execute()

    return new_conv.data[0]

async def save_message(conversation_id: str, role: str, content: str, metadata: dict = None):
    """Save message to DB."""
    result = supabase.table("conversation_messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "metadata": metadata or {}
    }).execute()

    return result.data[0]
```

**Update `main.py` to use it:**
```python
from app.services.supabase_client import save_conversation, save_message

@app.post("/api/v1/support/message")
async def handle_message(request: MessageRequest):
    # Get/create conversation
    conv = await save_conversation(
        request.tenant_id,
        request.user_id,
        request.channel
    )

    # Save user message
    await save_message(conv["id"], "user", request.content)

    # TODO: Generate response via LangGraph
    response_text = f"Echo: {request.content}"

    # Save assistant message
    await save_message(conv["id"], "assistant", response_text)

    return MessageResponse(
        response=response_text,
        intent="unknown",
        sources=None
    )
```

**✅ Checkpoint:**
- [ ] Messages saved to Supabase
- [ ] Conversations created automatically
- [ ] Check data in Supabase dashboard

---

## 🔍 Phase 2 : RAG Pipeline (2h)

### 2.1 — Qdrant Setup (30min)

**Create Qdrant collection:**
```python
# app/services/rag.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.config import settings

qdrant = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

# Create collection (run once)
def init_qdrant():
    try:
        qdrant.create_collection(
            collection_name="knowledge_base",
            vectors_config=VectorParams(
                size=1536,  # text-embedding-3-small
                distance=Distance.COSINE
            )
        )
        print("✅ Qdrant collection created")
    except Exception as e:
        print(f"Collection already exists or error: {e}")
```

**Test:**
```python
# In main.py, add startup event
@app.on_event("startup")
async def startup():
    from app.services.rag import init_qdrant
    init_qdrant()
```

**✅ Checkpoint:**
- [ ] Qdrant collection created
- [ ] Can connect to Qdrant

---

### 2.2 — Embeddings Service (30min)

**`app/services/embedding.py`:**
```python
import openai
from app.config import settings

openai.api_key = settings.OPENAI_API_KEY
openai.base_url = settings.OPENAI_BASE_URL

async def embed_text(text: str) -> list[float]:
    """Generate embedding for text."""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts."""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]
```

**✅ Checkpoint:**
- [ ] Embeddings work
- [ ] Test with sample text

---

### 2.3 — Index Sample Data (30min)

**Create test knowledge:**
```python
# scripts/seed_knowledge.py
import asyncio
from app.services.embedding import embed_text
from app.services.rag import qdrant
import uuid

async def seed_knowledge():
    tenant_id = "test-tenant-001"

    knowledge = [
        {
            "content": "Nous livrons en France métropolitaine sous 3 à 5 jours ouvrés. La livraison est gratuite à partir de 50€ d'achat.",
            "source_type": "website",
            "metadata": {"url": "https://exemple.com/livraison", "title": "Livraison"}
        },
        {
            "content": "Les retours sont acceptés sous 30 jours. Le produit doit être dans son emballage d'origine avec l'étiquette.",
            "source_type": "document",
            "metadata": {"filename": "politique_retours.pdf", "page": 1}
        },
        {
            "content": "Pour un remboursement, contactez support@boutique.com avec votre numéro de commande. Traitement sous 5 jours ouvrés.",
            "source_type": "website",
            "metadata": {"url": "https://exemple.com/remboursement"}
        }
    ]

    points = []
    for item in knowledge:
        chunk_id = str(uuid.uuid4())
        embedding = await embed_text(item["content"])

        points.append({
            "id": chunk_id,
            "vector": embedding,
            "payload": {
                "tenant_id": tenant_id,
                "source_type": item["source_type"],
                "content": item["content"],
                "metadata": item["metadata"]
            }
        })

    qdrant.upsert(
        collection_name="knowledge_base",
        points=points
    )

    print(f"✅ Indexed {len(points)} chunks")

if __name__ == "__main__":
    asyncio.run(seed_knowledge())
```

**Run:**
```bash
python scripts/seed_knowledge.py
```

**✅ Checkpoint:**
- [ ] Test data indexed in Qdrant
- [ ] Verify in Qdrant dashboard

---

### 2.4 — RAG Search Function (30min)

**Update `app/services/rag.py`:**
```python
from app.services.embedding import embed_text

async def search_knowledge(
    query: str,
    tenant_id: str,
    top_k: int = 3
) -> list[dict]:
    """Search knowledge base."""

    # Generate query embedding
    query_embedding = await embed_text(query)

    # Search Qdrant
    results = qdrant.search(
        collection_name="knowledge_base",
        query_vector=query_embedding,
        limit=top_k,
        query_filter={
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}}
            ]
        }
    )

    return [
        {
            "content": hit.payload["content"],
            "score": hit.score,
            "source_type": hit.payload["source_type"],
            "metadata": hit.payload["metadata"]
        }
        for hit in results
    ]

def format_rag_context(chunks: list[dict]) -> str:
    """Format chunks as context."""
    if not chunks:
        return ""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["metadata"].get("url") or chunk["metadata"].get("filename", "Unknown")
        context_parts.append(f"Source {i}: {source}\n{chunk['content']}")

    return "\n\n---\n\n".join(context_parts)
```

**Test search:**
```python
# Test in Python REPL
import asyncio
from app.services.rag import search_knowledge

results = asyncio.run(search_knowledge("délai livraison", "test-tenant-001"))
print(results)
```

**✅ Checkpoint:**
- [ ] Search returns relevant results
- [ ] Filtering by tenant_id works

---

## 🎨 Phase 3 : Frontend Chat UI (2h)

### 3.1 — Basic Chat Component (1h)

**`frontend/app/page.tsx`:**
```typescript
"use client"

import { useState } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/v1/support/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: 'test-tenant-001',
          user_id: 'test-user-001',
          channel: 'widget',
          content: input
        })
      })

      const data = await response.json()
      const assistantMessage: Message = { role: 'assistant', content: data.response }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto p-4">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-4 rounded-lg ${
              msg.role === 'user'
                ? 'bg-blue-100 ml-auto max-w-[80%]'
                : 'bg-gray-100 mr-auto max-w-[80%]'
            }`}
          >
            <p className="text-sm font-semibold mb-1">
              {msg.role === 'user' ? 'You' : 'Assistant'}
            </p>
            <p>{msg.content}</p>
          </div>
        ))}
        {loading && (
          <div className="bg-gray-100 p-4 rounded-lg mr-auto max-w-[80%]">
            <p className="text-gray-500">Thinking...</p>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type a message..."
          className="flex-1 p-3 border rounded-lg"
        />
        <button
          onClick={sendMessage}
          disabled={loading}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}
```

**Run:**
```bash
npm run dev
```

**✅ Checkpoint:**
- [ ] Chat UI renders
- [ ] Messages send to backend
- [ ] Responses display

---

### 3.2 — Polish UI (1h)

**Add better styling, loading states, error handling**

**✅ Checkpoint:**
- [ ] UI looks clean
- [ ] Mobile responsive
- [ ] Error messages shown

---

## 🌐 Phase 4 : Website Ingestion (1.5h)

### 4.1 — Crawl4AI Setup (30min)

**Install:**
```bash
pip install crawl4ai
```

**`app/services/crawler.py`:**
```python
from crawl4ai import AsyncWebCrawler
import asyncio

async def crawl_website(base_url: str, max_pages: int = 10) -> list[dict]:
    """Crawl website and extract content."""

    async with AsyncWebCrawler() as crawler:
        # Crawl base page
        result = await crawler.arun(
            url=base_url,
            word_count_threshold=50,
            excluded_tags=['nav', 'footer', 'aside'],
            exclude_external_links=True
        )

        pages = [{
            "url": result.url,
            "title": result.title,
            "content": result.markdown
        }]

        # Crawl internal links (up to max_pages)
        visited = {base_url}
        to_visit = [link for link in result.internal_links if link not in visited][:max_pages-1]

        for link in to_visit:
            try:
                result = await crawler.arun(url=link)
                pages.append({
                    "url": result.url,
                    "title": result.title,
                    "content": result.markdown
                })
                visited.add(link)
            except Exception as e:
                print(f"Failed to crawl {link}: {e}")

        return pages
```

**✅ Checkpoint:**
- [ ] Crawl4AI installed
- [ ] Test crawl on sample site

---

### 4.2 — Ingestion Endpoint (30min)

**`app/main.py`:**
```python
from app.services.crawler import crawl_website
from app.services.embedding import embed_text
from app.services.rag import qdrant

@app.post("/api/v1/admin/ingest-website")
async def ingest_website(tenant_id: str, website_url: str):
    """Crawl website and index in Qdrant."""

    # Crawl
    pages = await crawl_website(website_url, max_pages=10)

    # Index each page
    indexed_count = 0
    for page in pages:
        # Simple chunking (split by paragraphs)
        chunks = page["content"].split("\n\n")

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:
                continue

            # Embed
            embedding = await embed_text(chunk)

            # Index
            qdrant.upsert(
                collection_name="knowledge_base",
                points=[{
                    "id": f"{tenant_id}-{page['url']}-{i}",
                    "vector": embedding,
                    "payload": {
                        "tenant_id": tenant_id,
                        "source_type": "website",
                        "content": chunk,
                        "metadata": {
                            "url": page["url"],
                            "title": page["title"],
                            "chunk_index": i
                        }
                    }
                }]
            )
            indexed_count += 1

    return {
        "status": "success",
        "pages_crawled": len(pages),
        "chunks_indexed": indexed_count
    }
```

**Test:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/ingest-website?tenant_id=test-tenant-001&website_url=https://example.com"
```

**✅ Checkpoint:**
- [ ] Website crawls successfully
- [ ] Chunks indexed in Qdrant
- [ ] RAG search returns website content

---

## 🤖 Phase 5 : LangGraph Router (1.5h)

### 5.1 — Simple FAQ Handler (45min)

**`app/agents/nodes.py`:**
```python
from langchain_openai import ChatOpenAI
from app.config import settings

llm = ChatOpenAI(
    model=settings.DEFAULT_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

FAQ_SYSTEM_PROMPT = """
You are a helpful customer support assistant.

Common FAQs:
- Delivery: 3-5 business days in France. Free shipping over 50€.
- Returns: Accepted within 30 days, product must be unused with tags.
- Refunds: Contact support@boutique.com with order number. Processed in 5 business days.

Answer the customer's question using the FAQs above.
If you don't know, say "Let me check with our team" and escalate.
"""

async def handle_faq(query: str) -> str:
    """Handle FAQ questions."""
    response = await llm.ainvoke([
        {"role": "system", "content": FAQ_SYSTEM_PROMPT},
        {"role": "user", "content": query}
    ])
    return response.content
```

**Update `main.py`:**
```python
from app.agents.nodes import handle_faq

@app.post("/api/v1/support/message")
async def handle_message(request: MessageRequest):
    conv = await save_conversation(...)
    await save_message(conv["id"], "user", request.content)

    # Simple routing: check if RAG needed
    if "livraison" in request.content.lower() or "retour" in request.content.lower():
        response_text = await handle_faq(request.content)
    else:
        # Use RAG
        chunks = await search_knowledge(request.content, request.tenant_id)
        context = format_rag_context(chunks)

        # Generate response with context
        response = await llm.ainvoke([
            {"role": "system", "content": f"Use this context:\n{context}"},
            {"role": "user", "content": request.content}
        ])
        response_text = response.content

    await save_message(conv["id"], "assistant", response_text)

    return MessageResponse(response=response_text, intent="faq", sources=None)
```

**✅ Checkpoint:**
- [ ] FAQ questions answered correctly
- [ ] RAG fallback works

---

### 5.2 — LangGraph (Optional if time)

**Full LangGraph implementation with state management (30-45min if time permits)**

**✅ Checkpoint:**
- [ ] LangGraph routing works
- [ ] State persisted

---

## ✨ Phase 6 : Polish & Demo Prep (1.5h)

### 6.1 — Error Handling (30min)

- Add try/catch blocks
- Graceful fallbacks
- User-friendly error messages

**✅ Checkpoint:**
- [ ] No crashes on bad input
- [ ] Errors logged properly

---

### 6.2 — Demo Script (30min)

**Write demo narrative:**

```markdown
# Demo Script

## Intro (30s)
"Nous avons créé une plateforme AI qui automatise 70% du support client sur Instagram et web."

## Feature 1: FAQ (1min)
- Show chat widget
- Ask: "Quel est le délai de livraison ?"
- AI responds instantly from FAQ

## Feature 2: RAG (1.5min)
- Ask complex question requiring website knowledge
- AI searches Qdrant, returns answer with sources
- Show how we crawled website automatically

## Feature 3: Escalation (30s)
- Ask refund question
- AI says "Let me escalate to human"
- Show email sent (logs)

## Outro (30s)
"Zero configuration. Just connect Instagram + website URL. Live in 5 minutes."
```

**✅ Checkpoint:**
- [ ] Demo script written
- [ ] Practice run successful

---

### 6.3 — UI Polish (30min)

- Clean up UI
- Add loading states
- Better typography
- Mobile check

**✅ Checkpoint:**
- [ ] UI looks professional
- [ ] No obvious bugs

---

## 🎬 Final Checklist

### Must Have (Demo Breakers)
- [ ] Chat widget works end-to-end
- [ ] FAQ answers are correct
- [ ] RAG returns relevant results
- [ ] Website ingestion demo works
- [ ] No crashes during demo

### Nice to Have (Bonus Points)
- [ ] Instagram webhook simulation
- [ ] Admin panel showing conversations
- [ ] Escalation email sent
- [ ] BERTopic clustering demo

### Presentation
- [ ] Demo script ready
- [ ] Backup plan if live demo fails
- [ ] Screenshots/video recorded
- [ ] Pitch deck (optional)

---

## 🚨 Fallback Plan

If running out of time:

1. **Cut Features:**
   - ❌ Instagram webhook (mock it)
   - ❌ LangGraph (simple if/else routing)
   - ❌ BERTopic
   - ✅ Keep: FAQ + RAG + Chat UI

2. **Simplify:**
   - Use pre-indexed data (no live crawling in demo)
   - Hardcode tenant_id
   - Skip error handling

3. **Focus on Story:**
   - Perfect demo of core flow > many broken features

---

## 📊 Success Metrics

**Minimum viable demo:**
- ✅ User asks question
- ✅ AI responds in <3s
- ✅ Answer is relevant
- ✅ No crashes

**Great demo:**
- ✅ All of above
- ✅ RAG cites sources
- ✅ Website ingestion shown
- ✅ UI looks polished

**Amazing demo:**
- ✅ All of above
- ✅ Instagram integration
- ✅ Escalation flow
- ✅ Analytics/clustering

---

## 🔗 Related Documentation
- [PRD](./prd.md)
- [MVP Features](./mvp_features.md)
- [Project Architecture](../System/project_architecture.md)
- [RAG Pipeline](../System/rag_pipeline.md)
