# Project Architecture

**Related docs:** [database_schema.md](./database_schema.md), [rag_pipeline.md](./rag_pipeline.md), [prd.md](../Tasks/prd.md)

---

## 🎯 Project Goal

Build an **AI-powered customer support platform** that automates 70-90% of customer interactions across:
- Instagram DMs (primary channel)
- Website chat widget (embedded)
- Future: WhatsApp, Messenger, etc.

### Key Differentiators
1. **Zero-config onboarding** - Just connect Instagram + website URL
2. **Multi-source RAG** - FAQ + Documents + Website content + Conversation history
3. **Intelligent routing** - FAQ → RAG → Escalation → Scheduling
4. **Multi-tenant SaaS** - Each business = isolated tenant with RLS
5. **Automatic insights** - BERTopic clustering of customer topics

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER CHANNELS                             │
├──────────────────┬──────────────────┬──────────────────────────┤
│  Instagram DM    │  Website Widget  │  Future: WhatsApp, etc.  │
└────────┬─────────┴────────┬─────────┴──────────────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /api/v1/support/message                            │  │
│  │  - Tenant identification                                 │  │
│  │  - Message storage (Supabase)                            │  │
│  │  - Route to LangGraph                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph Agent Router                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Graph Nodes:                                            │  │
│  │  1. Classifier → Determine intent                        │  │
│  │  2. FAQ Handler → System prompt with FAQ list            │  │
│  │  3. RAG Handler → Qdrant hybrid search                   │  │
│  │  4. Escalation → Email worker                            │  │
│  │  5. Scheduling → Cal.com integration                     │  │
│  │                                                           │  │
│  │  State: PostgresCheckpointSaver (conversation memory)    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────┬────────┬────────┬────────┬────────────────────────────────┘
     │        │        │        │
     ▼        ▼        ▼        ▼
┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐
│   FAQ   │ │  Qdrant  │ │  Supabase │ │  Redis Workers   │
│ Prompt  │ │   RAG    │ │    DB     │ │  - Escalation    │
│         │ │          │ │           │ │  - Clustering    │
└─────────┘ └──────────┘ └───────────┘ └──────────────────┘
```

---

## 🧩 Core Components

### 1. **Backend API (FastAPI)**

**Location:** `backend/app/`

**Key Files:**
- `main.py` - FastAPI app, routes
- `agents/router.py` - LangGraph agent graph
- `agents/nodes.py` - Individual agent nodes (FAQ, RAG, escalation)
- `services/rag.py` - RAG pipeline with Qdrant
- `services/embedding.py` - Embedding generation
- `services/reranker.py` - Multi-query + LLM reranking
- `services/supabase_client.py` - Supabase connection
- `workers/escalation.py` - Email escalation worker
- `workers/clustering.py` - BERTopic daily clustering
- `workers/ingestion.py` - Website crawling with Crawl4AI

**Key Routes:**
```python
POST /api/v1/support/message
  - Receives user message
  - Stores in Supabase
  - Routes to LangGraph
  - Returns AI response

POST /api/v1/admin/ingest-website
  - Crawls website with Crawl4AI
  - Stores pages in Supabase
  - Embeds + indexes in Qdrant

GET /api/v1/conversations/{tenant_id}
  - Lists conversations for tenant

POST /api/v1/documents/upload
  - Uploads PDF/Word docs
  - Chunks + embeds + indexes
```

---

### 2. **LangGraph Agent Router**

**Purpose:** Orchestrate conversation flow with state management

**Graph Structure:**
```python
START → classify_intent → [
    "faq" → handle_faq → END,
    "product_question" → rag_search → END,
    "complaint" → escalate → END,
    "booking" → schedule → END,
    "unknown" → fallback → END
]
```

**State Schema:**
```python
class ConversationState(TypedDict):
    messages: list[Message]
    tenant_id: str
    user_id: str
    intent: str | None
    rag_context: str | None
    needs_escalation: bool
    booking_link: str | None
```

**Checkpointer:** PostgreSQL-based for conversation memory across sessions

---

### 3. **RAG Pipeline (Qdrant)**

**See:** [rag_pipeline.md](./rag_pipeline.md) for full details

**High-level flow:**
1. User query → Generate 3-5 query variants (multi-query)
2. For each variant → Qdrant dense search (top 5)
3. Deduplicate + merge results (top 15)
4. LLM reranking → top 3 most relevant chunks
5. Inject into system prompt → Generate response

**Data sources:**
- FAQ (system prompt, no RAG needed)
- Documents (PDF/Word uploaded by admin)
- Website pages (crawled via Crawl4AI)
- Conversation history (optional for context)

---

### 4. **Frontend (Next.js)**

**Location:** `frontend/`

**Key Components:**
- `app/page.tsx` - Admin dashboard
- `components/ChatWidget.tsx` - Embeddable chat widget
- `components/ConversationList.tsx` - Conversation history
- `components/DocumentUpload.tsx` - Upload docs for RAG

**Widget Embed:**
```html
<script src="https://your-domain.com/widget.js"></script>
<script>
  CustomerAI.init({ tenantId: 'boutique-123' })
</script>
```

---

### 5. **Background Workers (Redis + RQ)**

**Escalation Worker:**
- Triggered when intent = "escalate"
- Sends email with conversation summary
- Stores in `escalations` table

**Clustering Worker (Daily):**
- Runs BERTopic on all messages from past 24h
- Generates topic labels
- Stores in `topics_daily` table
- Used for dashboard insights

**Website Ingestion Worker:**
- Triggered by admin action
- Crawls up to 50 pages with Crawl4AI
- Stores in `website_pages`
- Chunks + embeds + Qdrant indexing

---

## 🔧 Tech Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Agent Framework:** LangGraph 0.2+
- **LLM:** OpenRouter (GPT-4o-mini, Mistral, etc.)
- **Embeddings:** OpenAI text-embedding-3-small
- **Vector DB:** Qdrant Cloud
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase Storage (for uploaded docs)
- **Auth:** Supabase Auth (admin panel)
- **Workers:** Redis + Python RQ
- **Web Scraping:** Crawl4AI
- **Clustering:** BERTopic

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Styling:** TailwindCSS
- **Components:** shadcn/ui
- **State:** React Query (TanStack Query)
- **Chat UI:** Custom component with streaming support

### DevOps
- **Hosting:** Vercel (frontend), Railway/Render (backend)
- **CI/CD:** GitHub Actions
- **Monitoring:** Sentry (errors), PostHog (analytics)

---

## 🔐 Multi-Tenancy & Security

### Tenant Isolation
- Each business = 1 row in `tenants` table
- All queries filtered by `tenant_id`
- Supabase RLS (Row Level Security) enforced
- Qdrant collections use `tenant_id` filter

### Authentication
- Admin panel: Supabase Auth (email/password)
- Widget: Public endpoint with rate limiting
- Instagram webhook: HMAC signature verification

### Data Privacy
- Conversations encrypted at rest (Supabase default)
- PII redaction option (future)
- GDPR-compliant data deletion

---

## 📊 Integration Points

### Instagram Graph API
- Webhook endpoint: `POST /webhooks/instagram`
- Verify token on setup
- Receive DMs → route to `/support/message`

### Cal.com API
- Generate booking links dynamically
- Optional: Auto-create bookings via API
- Store in `meetings` table

### Supabase
- Database (PostgreSQL)
- Storage (S3-compatible)
- Auth (admin users)
- Realtime (future: live chat handoff)

### Qdrant Cloud
- Collection per tenant (optional) or filtered by `tenant_id`
- Hybrid search (dense only for MVP)
- Metadata filtering by `source_type`

---

## 🚀 Deployment Architecture

```
┌────────────────────────────────────────────────────────┐
│  Vercel (Frontend)                                     │
│  - Next.js app                                         │
│  - Static widget.js                                    │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  Railway / Render (Backend)                            │
│  - FastAPI app (Gunicorn + Uvicorn)                    │
│  - Redis instance (workers)                            │
└────────────────────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
┌───────────────┐ ┌──────────┐ ┌──────────────┐
│  Supabase     │ │  Qdrant  │ │  OpenRouter  │
│  (managed)    │ │  Cloud   │ │  (LLM API)   │
└───────────────┘ └──────────┘ └──────────────┘
```

---

## 📈 Scalability Considerations

### Current (MVP)
- Single backend instance
- Qdrant Cloud free tier (1M vectors)
- Supabase free tier (500MB DB)
- Redis single instance

### Future (Production)
- Horizontal scaling: Multiple FastAPI instances behind load balancer
- Qdrant: Dedicated cluster or self-hosted
- Supabase: Pro plan with read replicas
- Redis: Cluster mode for high availability
- LLM: Fine-tuned models on Fireworks AI (cheaper than OpenAI)

---

## 🧪 Testing Strategy

### Unit Tests
- `pytest` for backend logic
- Mock LLM responses
- Mock Qdrant/Supabase

### Integration Tests
- E2E conversation flow
- RAG pipeline with test data
- Webhook handling

### Manual Testing
- Instagram test account
- Widget on localhost
- Admin dashboard flows

---

## 📝 Development Workflow

See: [development_workflow.md](../SOP/development_workflow.md)

**Key Commands:**
```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Workers
cd backend
rq worker --with-scheduler
```

---

## 🔗 Related Documentation
- [Database Schema](./database_schema.md)
- [RAG Pipeline](./rag_pipeline.md)
- [PRD](../Tasks/prd.md)
- [Hackathon Roadmap](../Tasks/hackathon_roadmap.md)
