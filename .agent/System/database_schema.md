# Database Schema

**Related docs:** [project_architecture.md](./project_architecture.md), [supabase_migrations.md](../SOP/supabase_migrations.md)

---

## 🗄️ Overview

All tables are stored in **Supabase (PostgreSQL)** with:
- Row Level Security (RLS) enabled
- Automatic `created_at` / `updated_at` timestamps
- UUID primary keys
- Multi-tenant isolation via `tenant_id`

**Supabase Project:** `kttpamevcntespkhnijx`

---

## 📋 Tables

### 1. `tenants`

Represents each business/customer using the platform.

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- e.g., "boutique-xyz"
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    settings JSONB DEFAULT '{}', -- custom config per tenant
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tenants_slug ON tenants(slug);

-- RLS
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Ma Boutique",
  "slug": "ma-boutique",
  "website_url": "https://ma-boutique.com",
  "contact_email": "support@ma-boutique.com",
  "settings": {
    "business_hours": "9-18",
    "timezone": "Europe/Paris",
    "escalation_email": "admin@ma-boutique.com"
  }
}
```

---

### 2. `social_accounts`

Links social media accounts (Instagram, WhatsApp, etc.) to tenants.

```sql
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- 'instagram', 'whatsapp', 'messenger'
    account_id VARCHAR(255) NOT NULL, -- platform-specific ID
    account_username VARCHAR(255),
    access_token TEXT, -- encrypted token
    token_expires_at TIMESTAMPTZ,
    webhook_verify_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(platform, account_id)
);

-- Indexes
CREATE INDEX idx_social_accounts_tenant ON social_accounts(tenant_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform, account_id);

-- RLS
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "instagram",
  "account_id": "17841405822304914",
  "account_username": "@ma_boutique_paris",
  "is_active": true
}
```

---

### 3. `conversations`

Tracks customer conversations (one per user per channel).

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL, -- platform-specific user ID (e.g., Instagram user ID)
    channel VARCHAR(50) NOT NULL, -- 'instagram', 'widget', 'whatsapp'
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'resolved', 'escalated'
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}', -- user info, tags, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, user_id, channel)
);

-- Indexes
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);

-- RLS
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "ig_12345678",
  "channel": "instagram",
  "status": "open",
  "metadata": {
    "user_name": "Sophie Martin",
    "language": "fr",
    "tags": ["livraison", "question_produit"]
  }
}
```

---

### 4. `conversation_messages`

Individual messages within conversations.

```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', -- intent, rag_sources, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id, created_at);
CREATE INDEX idx_messages_created ON conversation_messages(created_at DESC);

-- RLS
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "conversation_id": "770e8400-e29b-41d4-a716-446655440002",
  "role": "user",
  "content": "Bonjour, quel est le délai de livraison ?",
  "metadata": {}
},
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "conversation_id": "770e8400-e29b-41d4-a716-446655440002",
  "role": "assistant",
  "content": "Le délai de livraison est de 3 à 5 jours ouvrés en France métropolitaine.",
  "metadata": {
    "intent": "faq",
    "source": "system_prompt",
    "confidence": 0.95
  }
}
```

---

### 5. `documents`

Uploaded documents (PDFs, Word, etc.) for RAG.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL, -- Supabase Storage path
    file_size INTEGER,
    mime_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processed', 'failed'
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_status ON documents(status);

-- RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440005",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "politique_retours.pdf",
  "file_path": "tenants/ma-boutique/documents/politique_retours.pdf",
  "file_size": 245000,
  "mime_type": "application/pdf",
  "status": "processed",
  "chunk_count": 12,
  "metadata": {
    "description": "Politique de retours et remboursements",
    "upload_by": "admin@ma-boutique.com"
  }
}
```

---

### 6. `website_sources`

Tracks website URLs to crawl for RAG.

```sql
CREATE TABLE website_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    base_url VARCHAR(500) NOT NULL,
    max_pages INTEGER DEFAULT 50,
    crawl_frequency VARCHAR(50) DEFAULT 'manual', -- 'manual', 'daily', 'weekly'
    last_crawled_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'crawling', 'completed', 'failed'
    pages_crawled INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, base_url)
);

-- Indexes
CREATE INDEX idx_website_sources_tenant ON website_sources(tenant_id);
CREATE INDEX idx_website_sources_status ON website_sources(status);

-- RLS
ALTER TABLE website_sources ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440006",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "https://ma-boutique.com",
  "max_pages": 50,
  "crawl_frequency": "manual",
  "status": "completed",
  "pages_crawled": 23,
  "last_crawled_at": "2025-11-15T10:30:00Z"
}
```

---

### 7. `website_pages`

Individual pages crawled from websites.

```sql
CREATE TABLE website_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_source_id UUID NOT NULL REFERENCES website_sources(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    content TEXT,
    metadata JSONB DEFAULT '{}', -- links, images, etc.
    chunk_count INTEGER DEFAULT 0,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(website_source_id, url)
);

-- Indexes
CREATE INDEX idx_website_pages_source ON website_pages(website_source_id);
CREATE INDEX idx_website_pages_tenant ON website_pages(tenant_id);

-- RLS
ALTER TABLE website_pages ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "cc0e8400-e29b-41d4-a716-446655440007",
  "website_source_id": "bb0e8400-e29b-41d4-a716-446655440006",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://ma-boutique.com/livraison",
  "title": "Livraison - Ma Boutique",
  "content": "Nous livrons en France métropolitaine sous 3 à 5 jours...",
  "chunk_count": 4,
  "metadata": {
    "internal_links": ["/cgv", "/retours"],
    "last_modified": "2025-11-10"
  }
}
```

---

### 8. `knowledge_chunks`

Text chunks for RAG (from documents or website pages). **Metadata stored here, vectors in Qdrant.**

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'document', 'website', 'faq', 'conversation'
    source_id UUID, -- references documents.id or website_pages.id
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', -- chunk position, parent doc, etc.
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    indexed_in_qdrant BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_tenant ON knowledge_chunks(tenant_id);
CREATE INDEX idx_chunks_source ON knowledge_chunks(source_type, source_id);
CREATE INDEX idx_chunks_qdrant ON knowledge_chunks(indexed_in_qdrant);

-- RLS
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "dd0e8400-e29b-41d4-a716-446655440008",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_type": "website",
  "source_id": "cc0e8400-e29b-41d4-a716-446655440007",
  "content": "Nous livrons en France métropolitaine sous 3 à 5 jours ouvrés. La livraison est gratuite à partir de 50€.",
  "metadata": {
    "chunk_index": 0,
    "parent_url": "https://ma-boutique.com/livraison",
    "char_count": 120
  },
  "indexed_in_qdrant": true
}
```

---

### 9. `escalations`

Tracks escalated conversations sent to human agents.

```sql
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    reason VARCHAR(255) NOT NULL, -- 'complex_issue', 'refund_request', 'vip', etc.
    summary TEXT, -- AI-generated summary
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'resolved'
    assigned_to VARCHAR(255), -- email of human agent
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_escalations_tenant ON escalations(tenant_id);
CREATE INDEX idx_escalations_conversation ON escalations(conversation_id);
CREATE INDEX idx_escalations_status ON escalations(status);

-- RLS
ALTER TABLE escalations ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "ee0e8400-e29b-41d4-a716-446655440009",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "770e8400-e29b-41d4-a716-446655440002",
  "reason": "refund_request",
  "summary": "Le client demande un remboursement pour un produit défectueux reçu il y a 2 semaines.",
  "status": "pending",
  "assigned_to": "support@ma-boutique.com"
}
```

---

### 10. `topics_daily`

Daily clustering of conversation topics (BERTopic).

```sql
CREATE TABLE topics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    topic_id INTEGER NOT NULL, -- BERTopic cluster ID
    topic_label VARCHAR(255), -- "Livraison", "Remboursement", etc.
    keywords TEXT[], -- top keywords for topic
    message_count INTEGER DEFAULT 0,
    percentage DECIMAL(5,2), -- % of total messages
    sample_messages JSONB DEFAULT '[]', -- array of sample message IDs
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, date, topic_id)
);

-- Indexes
CREATE INDEX idx_topics_tenant_date ON topics_daily(tenant_id, date DESC);

-- RLS
ALTER TABLE topics_daily ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "ff0e8400-e29b-41d4-a716-446655440010",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-11-15",
  "topic_id": 0,
  "topic_label": "Livraison et délais",
  "keywords": ["livraison", "délai", "tracking", "colis"],
  "message_count": 45,
  "percentage": 32.5,
  "sample_messages": [
    "880e8400-e29b-41d4-a716-446655440003"
  ]
}
```

---

### 11. `meetings`

Scheduled meetings via Cal.com (optional).

```sql
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id VARCHAR(255) NOT NULL,
    meeting_url VARCHAR(500),
    scheduled_at TIMESTAMPTZ,
    duration_minutes INTEGER DEFAULT 30,
    status VARCHAR(50) DEFAULT 'scheduled', -- 'scheduled', 'completed', 'cancelled'
    cal_event_id VARCHAR(255), -- Cal.com event ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_meetings_tenant ON meetings(tenant_id);
CREATE INDEX idx_meetings_conversation ON meetings(conversation_id);

-- RLS
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
```

**Example data:**
```json
{
  "id": "1a0e8400-e29b-41d4-a716-446655440011",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "770e8400-e29b-41d4-a716-446655440002",
  "user_id": "ig_12345678",
  "meeting_url": "https://cal.com/ma-boutique/15min?date=2025-11-20T14:00:00Z",
  "scheduled_at": "2025-11-20T14:00:00Z",
  "status": "scheduled"
}
```

---

### 12. `model_versions` (Optional - Fine-tuning)

Tracks fine-tuned model versions.

```sql
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE, -- NULL for global models
    model_name VARCHAR(255) NOT NULL, -- 'gpt-4o-mini-ft-boutique-v1'
    base_model VARCHAR(255) NOT NULL,
    training_dataset_id VARCHAR(255),
    version VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'training', -- 'training', 'ready', 'deprecated'
    metrics JSONB DEFAULT '{}', -- accuracy, loss, etc.
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_model_versions_tenant ON model_versions(tenant_id);
CREATE INDEX idx_model_versions_active ON model_versions(is_active);

-- RLS
ALTER TABLE model_versions ENABLE ROW LEVEL SECURITY;
```

---

## 🔐 Row Level Security (RLS) Policies

All tables have RLS enabled. Example for `conversations`:

```sql
-- Admin can see all conversations for their tenant
CREATE POLICY "Admins can view their tenant's conversations"
ON conversations
FOR SELECT
USING (
  tenant_id IN (
    SELECT tenant_id FROM admin_users WHERE user_id = auth.uid()
  )
);

-- Similar policies for INSERT, UPDATE, DELETE
```

---

## 🔗 Entity Relationship Diagram

```
tenants (1) ──── (N) social_accounts
   │
   ├─── (N) conversations
   │         └─── (N) conversation_messages
   │
   ├─── (N) documents
   │         └─── (N) knowledge_chunks
   │
   ├─── (N) website_sources
   │         └─── (N) website_pages
   │                   └─── (N) knowledge_chunks
   │
   ├─── (N) escalations
   │
   ├─── (N) topics_daily
   │
   └─── (N) meetings
```

---

## 📊 Key Metrics & Queries

### Get conversation stats for a tenant
```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as conversation_count,
  COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count
FROM conversations
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Get top topics for a tenant
```sql
SELECT
  topic_label,
  SUM(message_count) as total_messages,
  AVG(percentage) as avg_percentage
FROM topics_daily
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000'
  AND date >= NOW() - INTERVAL '30 days'
GROUP BY topic_label
ORDER BY total_messages DESC
LIMIT 10;
```

---

## 🛠️ Migration Strategy

See: [supabase_migrations.md](../SOP/supabase_migrations.md)

**Initial setup:**
```bash
# Create migration
supabase migration new initial_schema

# Apply migration
supabase db push
```

---

## 🔗 Related Documentation
- [Project Architecture](./project_architecture.md)
- [RAG Pipeline](./rag_pipeline.md)
- [Supabase Migrations SOP](../SOP/supabase_migrations.md)
