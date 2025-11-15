# Adding RAG Sources - Standard Operating Procedures

**Related docs:** [rag_pipeline.md](../System/rag_pipeline.md), [database_schema.md](../System/database_schema.md)

---

## 🎯 Purpose

This document explains how to add new knowledge sources to the RAG system:
1. Website crawling
2. Document upload (PDF, Word)
3. Manual FAQ entries
4. Conversation history (advanced)

---

## 🌐 Adding Website Sources

### Step 1: Prepare Website URL

**Requirements:**
- Valid HTTPS URL
- Publicly accessible (no auth required)
- Not blocking crawlers (check `robots.txt`)

**Example URLs:**
```
✅ https://ma-boutique.com
✅ https://exemple.com/support
❌ https://admin.boutique.com (likely blocked)
❌ http://localhost:3000 (not public)
```

---

### Step 2: Trigger Website Crawl

**API Endpoint:**
```bash
POST /api/v1/admin/ingest-website

Body:
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "website_url": "https://ma-boutique.com",
  "max_pages": 20  // optional, default 50
}
```

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/ingest-website \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant-001",
    "website_url": "https://ma-boutique.com",
    "max_pages": 20
  }'
```

**Response:**
```json
{
  "status": "success",
  "website_source_id": "bb0e8400-e29b-41d4-a716-446655440006",
  "pages_crawled": 18,
  "chunks_indexed": 142,
  "duration_seconds": 45.3
}
```

---

### Step 3: Verify Indexing

**Check Qdrant:**
```python
from app.services.rag import qdrant

# Search for website content
results = qdrant.search(
    collection_name="knowledge_base",
    query_vector=embedding,
    query_filter={
        "must": [
            {"key": "tenant_id", "match": {"value": "test-tenant-001"}},
            {"key": "source_type", "match": {"value": "website"}}
        ]
    },
    limit=5
)

print(f"Found {len(results)} website chunks")
```

**Check Supabase:**
```sql
SELECT COUNT(*) FROM website_pages
WHERE tenant_id = 'test-tenant-001';

SELECT COUNT(*) FROM knowledge_chunks
WHERE tenant_id = 'test-tenant-001'
  AND source_type = 'website';
```

---

### Step 4: Test RAG Search

**Query the indexed content:**
```python
from app.services.rag import search_knowledge

results = await search_knowledge(
    query="politique de livraison",
    tenant_id="test-tenant-001",
    top_k=3
)

for i, result in enumerate(results, 1):
    print(f"\n{i}. Score: {result['score']:.3f}")
    print(f"   Source: {result['metadata'].get('url', 'Unknown')}")
    print(f"   Content: {result['content'][:200]}...")
```

**Expected output:**
```
1. Score: 0.892
   Source: https://ma-boutique.com/livraison
   Content: Nous livrons en France métropolitaine sous 3 à 5 jours...

2. Score: 0.845
   Source: https://ma-boutique.com/cgv
   Content: Les frais de livraison sont calculés en fonction...
```

---

### Troubleshooting Website Crawl

**Problem: Crawl returns 0 pages**

**Possible causes:**
1. Website blocks crawlers
2. Invalid URL
3. JavaScript-heavy site (Crawl4AI should handle this, but check)
4. Timeout

**Solutions:**
```python
# Increase timeout
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url=base_url,
        timeout=60  # Increase from default 30s
    )

# Check robots.txt manually
# Visit: https://ma-boutique.com/robots.txt
```

---

**Problem: Crawled content is messy (includes nav/footer)**

**Solution:**
```python
# Exclude more tags
result = await crawler.arun(
    url=base_url,
    excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style'],
    word_count_threshold=100  # Skip pages with <100 words
)
```

---

**Problem: Too many pages crawled**

**Solution:**
```python
# Limit pages
pages = await crawl_website(base_url, max_pages=10)

# Or exclude patterns
result = await crawler.arun(
    url=base_url,
    exclude_patterns=['/admin/*', '/account/*', '/checkout/*']
)
```

---

## 📄 Adding Document Sources

### Step 1: Upload Document

**API Endpoint:**
```bash
POST /api/v1/admin/documents/upload

Form Data:
- file: <PDF or Word file>
- tenant_id: string
```

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/documents/upload \
  -F "file=@politique_retours.pdf" \
  -F "tenant_id=test-tenant-001"
```

**Using Python:**
```python
import requests

files = {'file': open('politique_retours.pdf', 'rb')}
data = {'tenant_id': 'test-tenant-001'}

response = requests.post(
    'http://localhost:8000/api/v1/admin/documents/upload',
    files=files,
    data=data
)

print(response.json())
```

**Response:**
```json
{
  "status": "success",
  "document_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "filename": "politique_retours.pdf",
  "chunks_indexed": 12,
  "file_size": 245000
}
```

---

### Step 2: Document Processing

**Backend automatically:**
1. Saves file to Supabase Storage
2. Extracts text (PDF/Word)
3. Chunks text (500 chars, 50 overlap)
4. Generates embeddings
5. Indexes in Qdrant
6. Updates `documents` table status

**Check processing status:**
```sql
SELECT id, filename, status, chunk_count
FROM documents
WHERE tenant_id = 'test-tenant-001'
ORDER BY created_at DESC;
```

**Status values:**
- `pending` - Uploaded, not yet processed
- `processing` - Currently extracting/indexing
- `processed` - Successfully indexed
- `failed` - Processing failed (check logs)

---

### Step 3: Verify Document Chunks

**Check Supabase:**
```sql
SELECT
  kc.id,
  kc.content,
  kc.metadata,
  d.filename
FROM knowledge_chunks kc
JOIN documents d ON kc.source_id = d.id
WHERE kc.tenant_id = 'test-tenant-001'
  AND kc.source_type = 'document'
ORDER BY kc.created_at DESC
LIMIT 10;
```

**Check Qdrant:**
```python
results = qdrant.search(
    collection_name="knowledge_base",
    query_vector=embedding,
    query_filter={
        "must": [
            {"key": "tenant_id", "match": {"value": "test-tenant-001"}},
            {"key": "source_type", "match": {"value": "document"}}
        ]
    },
    limit=5
)
```

---

### Troubleshooting Document Upload

**Problem: PDF extraction fails**

**Possible causes:**
1. Scanned PDF (images, not text)
2. Encrypted PDF
3. Corrupted file

**Solutions:**
```python
# For scanned PDFs, use OCR
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path('scanned.pdf')
text = ""
for img in images:
    text += pytesseract.image_to_string(img)

# For encrypted PDFs
from pypdf import PdfReader
reader = PdfReader('encrypted.pdf', password='password')
```

---

**Problem: Word document extraction fails**

**Solution:**
```python
# Ensure python-docx installed
pip install python-docx

# Handle different Word formats
from docx import Document

try:
    doc = Document('file.docx')
    text = "\n".join([p.text for p in doc.paragraphs])
except Exception as e:
    # Fallback: try converting .doc to .docx
    # Or use another library like python-docx2txt
    import docx2txt
    text = docx2txt.process('file.doc')
```

---

## 📝 Adding FAQ Sources

### Step 1: Define FAQ Entries

**Structure:**
```json
{
  "faqs": [
    {
      "question": "Quel est le délai de livraison ?",
      "answer": "3 à 5 jours ouvrés en France métropolitaine. Gratuit >50€.",
      "category": "livraison"
    },
    {
      "question": "Comment faire un retour ?",
      "answer": "Retours acceptés sous 30 jours, produit non utilisé avec étiquette.",
      "category": "retours"
    },
    {
      "question": "Quelle est la politique de remboursement ?",
      "answer": "Contactez support@boutique.com avec numéro de commande. Traitement sous 5 jours.",
      "category": "remboursement"
    }
  ]
}
```

---

### Step 2: Store in Supabase

**Option 1: Store in `tenant.settings` (Recommended for MVP)**

```sql
UPDATE tenants
SET settings = jsonb_set(
  settings,
  '{faq}',
  '[
    {
      "question": "Quel est le délai de livraison ?",
      "answer": "3 à 5 jours ouvrés en France métropolitaine. Gratuit >50€."
    },
    {
      "question": "Comment faire un retour ?",
      "answer": "Retours acceptés sous 30 jours, produit non utilisé avec étiquette."
    }
  ]'::jsonb
)
WHERE id = 'test-tenant-001';
```

**Option 2: Create dedicated `faqs` table**

```sql
CREATE TABLE IF NOT EXISTS faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_faqs_tenant ON faqs(tenant_id);
ALTER TABLE faqs ENABLE ROW LEVEL SECURITY;
```

**Insert FAQs:**
```sql
INSERT INTO faqs (tenant_id, question, answer, category) VALUES
('test-tenant-001', 'Quel est le délai de livraison ?', '3 à 5 jours...', 'livraison'),
('test-tenant-001', 'Comment faire un retour ?', 'Retours acceptés...', 'retours');
```

---

### Step 3: Use FAQ in System Prompt

**Load FAQ into prompt:**
```python
# app/agents/nodes.py

async def get_faq_prompt(tenant_id: str) -> str:
    """Generate system prompt with FAQ."""

    # Fetch FAQs from Supabase
    faqs = supabase.table("faqs").select("question, answer").eq(
        "tenant_id", tenant_id
    ).eq("is_active", True).execute()

    # Format as prompt
    faq_text = "\n\n".join([
        f"Q: {faq['question']}\nA: {faq['answer']}"
        for faq in faqs.data
    ])

    system_prompt = f"""
You are a helpful customer support assistant.

Common FAQs:
{faq_text}

Answer the customer's question using the FAQs above.
If the answer is not in the FAQs, use your knowledge base to help.
    """

    return system_prompt
```

---

### Step 4: Test FAQ Responses

**Test query:**
```python
prompt = await get_faq_prompt("test-tenant-001")

response = await llm.ainvoke([
    {"role": "system", "content": prompt},
    {"role": "user", "content": "Quel est le délai de livraison ?"}
])

print(response.content)
# Expected: "Le délai de livraison est de 3 à 5 jours ouvrés..."
```

---

## 🔄 Updating Existing Sources

### Re-crawl Website

**When to re-crawl:**
- Website content updated
- New pages added
- Errors in original crawl

**How:**
```python
# Same as initial crawl, but overwrites existing data
await ingest_website(
    tenant_id="test-tenant-001",
    website_url="https://ma-boutique.com",
    max_pages=50
)

# Optional: Delete old chunks first
supabase.table("knowledge_chunks").delete().eq(
    "tenant_id", tenant_id
).eq("source_type", "website").execute()
```

---

### Update Document

**Replace document:**
1. Delete old chunks from Qdrant
2. Upload new version
3. Re-index

```python
# Delete old chunks
qdrant.delete(
    collection_name="knowledge_base",
    points_selector={
        "filter": {
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}},
                {"key": "source_id", "match": {"value": old_document_id}}
            ]
        }
    }
)

# Upload new document
# (same as Step 1 above)
```

---

### Update FAQ

**Edit FAQ entry:**
```sql
UPDATE faqs
SET answer = 'Nouveau texte de réponse',
    updated_at = NOW()
WHERE tenant_id = 'test-tenant-001'
  AND question = 'Quel est le délai de livraison ?';
```

**Changes take effect immediately** (FAQ loaded dynamically from DB).

---

## 🗑️ Removing Sources

### Delete Website Source

```sql
-- This cascades to website_pages and knowledge_chunks
DELETE FROM website_sources
WHERE id = 'bb0e8400-e29b-41d4-a716-446655440006';
```

**Also delete from Qdrant:**
```python
qdrant.delete(
    collection_name="knowledge_base",
    points_selector={
        "filter": {
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}},
                {"key": "source_type", "match": {"value": "website"}},
                {"key": "source_id", "match": {"value": website_source_id}}
            ]
        }
    }
)
```

---

### Delete Document

```sql
-- Cascades to knowledge_chunks
DELETE FROM documents
WHERE id = 'aa0e8400-e29b-41d4-a716-446655440005';
```

**Delete from Qdrant:**
```python
qdrant.delete(
    collection_name="knowledge_base",
    points_selector={
        "filter": {
            "must": [
                {"key": "source_id", "match": {"value": document_id}}
            ]
        }
    }
)
```

**Delete from Supabase Storage:**
```python
supabase.storage.from_("documents").remove([file_path])
```

---

### Delete FAQ

```sql
DELETE FROM faqs
WHERE id = 'faq-id-here';

-- Or soft delete
UPDATE faqs
SET is_active = FALSE
WHERE id = 'faq-id-here';
```

---

## 📊 Monitoring RAG Sources

### Check Source Counts

```sql
-- Total chunks per source type
SELECT
  source_type,
  COUNT(*) as chunk_count
FROM knowledge_chunks
WHERE tenant_id = 'test-tenant-001'
GROUP BY source_type;
```

**Output:**
```
source_type | chunk_count
------------+-------------
website     | 142
document    | 38
faq         | 0  (FAQs not indexed in Qdrant for MVP)
```

---

### Check RAG Performance

```sql
-- Average RAG response time
SELECT
  DATE(created_at) as date,
  AVG((metadata->>'rag_time_ms')::INTEGER) as avg_rag_time_ms,
  COUNT(*) as message_count
FROM conversation_messages
WHERE metadata ? 'rag_time_ms'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

### Check Most Used Sources

```sql
-- Top sources used in RAG responses
SELECT
  metadata->>'source_url' as source,
  COUNT(*) as usage_count
FROM conversation_messages
WHERE metadata ? 'rag_sources'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY metadata->>'source_url'
ORDER BY usage_count DESC
LIMIT 10;
```

---

## 🔧 Advanced: Batch Indexing

### Index Multiple Documents

```python
import os
from pathlib import Path

async def batch_index_documents(tenant_id: str, folder_path: str):
    """Index all PDFs in a folder."""

    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDFs to index")

    for pdf_file in pdf_files:
        print(f"Indexing: {pdf_file.name}")

        try:
            with open(pdf_file, 'rb') as f:
                await upload_document(tenant_id, f, pdf_file.name)
            print(f"✅ Indexed: {pdf_file.name}")
        except Exception as e:
            print(f"❌ Failed: {pdf_file.name} - {e}")

# Usage
await batch_index_documents("test-tenant-001", "./documents")
```

---

## 🔗 Related Documentation
- [RAG Pipeline](../System/rag_pipeline.md)
- [Database Schema](../System/database_schema.md)
- [Development Workflow](./development_workflow.md)
