# MVP Features Breakdown

**Related docs:** [prd.md](./prd.md), [hackathon_roadmap.md](./hackathon_roadmap.md)

---

## 🎯 MVP Definition

**Goal:** Deliver a working demo that showcases the core value proposition in 12 hours.

**Core Value:** AI that answers customer questions using their own business knowledge (FAQ + Documents + Website).

---

## ✅ Must-Have Features (P0)

### 1. Chat Interface
**User Story:** As a customer, I want to ask questions and get instant responses.

**Acceptance Criteria:**
- [ ] Chat UI renders on web page
- [ ] User can type and send messages
- [ ] AI responses appear in <3 seconds
- [ ] Conversation persists during session
- [ ] Mobile responsive

**Implementation:**
- Next.js frontend with simple chat component
- API call to `/support/message`
- Messages stored in Supabase

**Estimated Time:** 2h

---

### 2. FAQ System (System Prompt)
**User Story:** As a customer, I want instant answers to common questions (delivery, returns, refunds).

**Acceptance Criteria:**
- [ ] FAQ defined in system prompt
- [ ] AI answers FAQ questions 100% accurately
- [ ] Latency <1s for FAQ responses
- [ ] At least 5-10 FAQ entries

**FAQ Examples:**
```
Q: Quel est le délai de livraison ?
A: 3 à 5 jours ouvrés en France métropolitaine. Gratuit >50€.

Q: Comment faire un retour ?
A: Retours acceptés sous 30 jours, produit non utilisé avec étiquette.

Q: Quelle est la politique de remboursement ?
A: Contactez support@boutique.com avec numéro de commande. Traitement sous 5 jours.
```

**Implementation:**
- Hardcoded in system prompt
- LLM (GPT-4o-mini) generates responses
- No RAG needed (faster)

**Estimated Time:** 1h

---

### 3. RAG Search (Qdrant)
**User Story:** As a customer, I want answers based on the business's actual website and documents.

**Acceptance Criteria:**
- [ ] Qdrant collection created
- [ ] 3-5 test documents indexed
- [ ] Search returns relevant chunks
- [ ] Tenant filtering works
- [ ] Latency <2s

**Test Knowledge:**
- Sample website pages (livraison, retours, CGV)
- Sample PDF (politique commerciale)

**Implementation:**
- Qdrant Cloud setup
- OpenAI embeddings (text-embedding-3-small)
- Simple dense search (no hybrid)
- Top 3 chunks returned

**Estimated Time:** 2h

---

### 4. Message Storage
**User Story:** As an admin, I want all conversations stored for review.

**Acceptance Criteria:**
- [ ] Conversations saved to `conversations` table
- [ ] Messages saved to `conversation_messages` table
- [ ] User ID + channel tracked
- [ ] Timestamps recorded

**Implementation:**
- Supabase tables (via MCP)
- Save on every message send/receive

**Estimated Time:** 1h

---

### 5. Backend API
**User Story:** As a developer, I need a reliable API to handle messages.

**Acceptance Criteria:**
- [ ] `POST /support/message` works
- [ ] Request validation (Pydantic)
- [ ] Error handling (try/catch)
- [ ] CORS enabled for frontend
- [ ] Health check endpoint

**Implementation:**
- FastAPI
- Pydantic models for validation
- Basic error responses (500, 400)

**Estimated Time:** 2h

---

## 🚀 Should-Have Features (P1)

### 6. Website Ingestion
**User Story:** As an admin, I want to automatically index my website for RAG.

**Acceptance Criteria:**
- [ ] Admin provides URL
- [ ] System crawls 10-20 pages
- [ ] Content extracted cleanly
- [ ] Pages indexed in Qdrant
- [ ] Status visible to admin

**Implementation:**
- Crawl4AI for scraping
- Async processing (simple for MVP, no workers)
- Chunking + embedding + Qdrant indexing
- Admin endpoint `/admin/ingest-website`

**Estimated Time:** 1.5h

---

### 7. Simple Routing (Intent Detection)
**User Story:** As a system, I want to route FAQ vs RAG intelligently.

**Acceptance Criteria:**
- [ ] FAQ questions → FAQ handler
- [ ] Complex questions → RAG handler
- [ ] Unknown → fallback message

**Implementation:**
- Simple keyword matching (MVP)
- Or LLM-based classifier (if time)
- No full LangGraph yet

**Estimated Time:** 1h

---

### 8. Context Injection
**User Story:** As an AI, I want to use retrieved knowledge to answer accurately.

**Acceptance Criteria:**
- [ ] RAG chunks formatted as context
- [ ] System prompt includes context
- [ ] LLM uses context to generate response
- [ ] Sources cited in response (optional)

**Implementation:**
- Format chunks as markdown
- Inject into system prompt
- LLM generates answer

**Estimated Time:** 30min

---

## 🎁 Nice-to-Have Features (P2)

### 9. Escalation (Email)
**User Story:** As a customer, I want complex issues escalated to humans.

**Acceptance Criteria:**
- [ ] AI detects need for escalation
- [ ] Email sent to support team
- [ ] Customer informed of escalation
- [ ] Conversation marked "escalated"

**Implementation:**
- Simple email via SMTP or SendGrid
- Triggered by keywords (refund, fraud, etc.)
- No full worker queue (MVP)

**Estimated Time:** 1h (if time permits)

---

### 10. Admin Panel (Conversations List)
**User Story:** As an admin, I want to see all conversations.

**Acceptance Criteria:**
- [ ] List all conversations for tenant
- [ ] View conversation detail
- [ ] Filter by status (open, resolved)
- [ ] Search by user ID

**Implementation:**
- Next.js page `/admin/conversations`
- Supabase query with pagination
- Simple table UI

**Estimated Time:** 2h (if time permits)

---

### 11. Cal.com Scheduling
**User Story:** As a customer, I want to book a meeting easily.

**Acceptance Criteria:**
- [ ] AI detects booking request
- [ ] Provides Cal.com link
- [ ] Link works and allows booking

**Implementation:**
- Static Cal.com link (MVP)
- Triggered by keywords ("rendez-vous", "appel")
- No API integration (manual for now)

**Estimated Time:** 30min (if time permits)

---

## ❌ Out of Scope (Not in MVP)

### Explicitly NOT Included
- ❌ Instagram webhook integration (simulated)
- ❌ WhatsApp / Messenger
- ❌ Multi-language support
- ❌ Voice messages
- ❌ Image handling
- ❌ Fine-tuned models
- ❌ BERTopic clustering
- ❌ Advanced analytics dashboard
- ❌ Live chat handoff
- ❌ Payments integration
- ❌ Multi-query expansion (simple search only)
- ❌ LLM reranking (score-based only)
- ❌ Custom branding (widget)
- ❌ Rate limiting
- ❌ Authentication (admin panel)
- ❌ Horizontal scaling setup

---

## 📊 Feature Priority Matrix

| Feature | Impact | Effort | Priority | Status |
|---------|--------|--------|----------|--------|
| Chat UI | High | Medium | P0 | ✅ Must |
| FAQ System | High | Low | P0 | ✅ Must |
| RAG Search | High | Medium | P0 | ✅ Must |
| Message Storage | Medium | Low | P0 | ✅ Must |
| Backend API | High | Medium | P0 | ✅ Must |
| Website Ingestion | High | Medium | P1 | 🔶 Should |
| Simple Routing | Medium | Low | P1 | 🔶 Should |
| Context Injection | High | Low | P1 | 🔶 Should |
| Escalation | Medium | Medium | P2 | 💡 Nice |
| Admin Panel | Low | High | P2 | 💡 Nice |
| Cal.com | Low | Low | P2 | 💡 Nice |

---

## 🎯 Success Criteria

### Minimum Demo
**What makes this work?**
1. User asks question
2. AI responds with correct answer
3. Answer is based on real business data
4. No crashes

**Demo Flow:**
```
User: "Quel est le délai de livraison ?"
AI: "Le délai de livraison est de 3 à 5 jours ouvrés en France métropolitaine.
     La livraison est gratuite à partir de 50€ d'achat."
     (Source: FAQ)

User: "Quelle est votre politique de protection des données ?"
AI: "Selon notre politique de confidentialité, nous..."
     (Source: website crawl - page CGV)

User: "Je veux un remboursement pour produit défectueux"
AI: "Je comprends votre situation. Je transmets votre demande à notre équipe
     qui vous contactera sous 24h. Pouvez-vous m'envoyer votre numéro de commande ?"
     (Escalation triggered)
```

### Great Demo
All of above +
- Website ingestion shown live
- RAG cites sources
- UI looks polished
- Mobile responsive

### Amazing Demo
All of above +
- Instagram integration (simulated)
- Escalation email sent
- Admin panel showing conversations

---

## 🛠️ Technical Requirements

### Backend
- ✅ FastAPI 0.104+
- ✅ Supabase client
- ✅ Qdrant client
- ✅ OpenAI/OpenRouter
- ✅ Crawl4AI
- ✅ Pydantic models

### Frontend
- ✅ Next.js 14+
- ✅ TailwindCSS
- ✅ TypeScript
- ✅ React Query (optional)

### Infrastructure
- ✅ Supabase (free tier)
- ✅ Qdrant Cloud (free tier)
- ✅ OpenRouter (pay-as-you-go)
- ✅ Vercel (frontend hosting)
- ✅ Railway/Render (backend hosting)

### Environment Variables
```env
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Qdrant
QDRANT_URL=
QDRANT_API_KEY=

# OpenAI/OpenRouter
OPENAI_API_KEY=
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Models
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

## 🧪 Testing Checklist

### Functional Tests
- [ ] Send message → receive response
- [ ] FAQ question → correct answer
- [ ] Complex question → RAG search → relevant answer
- [ ] Website ingestion → pages indexed
- [ ] Conversation saved to DB

### UI/UX Tests
- [ ] Chat UI loads
- [ ] Messages send/receive
- [ ] Loading states work
- [ ] Error messages shown
- [ ] Mobile responsive

### Edge Cases
- [ ] Empty message
- [ ] Very long message
- [ ] Special characters
- [ ] No RAG results found
- [ ] LLM timeout
- [ ] Qdrant connection error

---

## 🔗 Related Documentation
- [PRD](./prd.md)
- [Hackathon Roadmap](./hackathon_roadmap.md)
- [Project Architecture](../System/project_architecture.md)
- [RAG Pipeline](../System/rag_pipeline.md)
