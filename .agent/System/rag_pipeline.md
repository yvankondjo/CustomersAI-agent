# RAG Pipeline Architecture

**Related docs:** [project_architecture.md](./project_architecture.md), [database_schema.md](./database_schema.md), [adding_rag_sources.md](../SOP/adding_rag_sources.md)

---

## 🎯 Overview

The RAG (Retrieval Augmented Generation) pipeline enables the AI to answer questions using:
1. **Documents** (PDFs, Word files uploaded by admin)
2. **Website content** (crawled with Crawl4AI)
3. **FAQ database** (stored in system prompt, no RAG needed)
4. **Conversation history** (optional for context)

**Key Design Decisions:**
- ✅ **Dense embeddings only** (hybrid search = overkill for MVP)
- ✅ **Multi-query expansion** for better recall (3-5 query variants)
- ✅ **LLM-based reranking** for precision (top 3 chunks)
- ✅ **Crawl4AI** for website ingestion (better than BeautifulSoup)
- ✅ **Qdrant Cloud** for vector storage (free tier = 1M vectors)

---

## 🏗️ Pipeline Architecture

```
User Query: "Quel est le délai de livraison ?"
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  1. Query Expansion (Multi-Query)                     │
│  - Generate 3-5 semantically similar queries          │
│  - "délai livraison"                                   │
│  - "combien de temps pour recevoir commande"          │
│  - "livraison rapide disponible"                      │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  2. Dense Vector Search (Qdrant)                      │
│  For each query:                                       │
│  - Generate embedding (OpenAI text-embedding-3-small) │
│  - Search Qdrant with filters:                        │
│    - tenant_id = "ma-boutique"                        │
│    - source_type IN ["document", "website"]           │
│  - Get top 5 chunks per query                         │
│  Total: ~15 chunks (with duplicates)                  │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  3. Deduplication                                      │
│  - Remove duplicate chunks by ID                      │
│  - Keep unique top 10-12 chunks                       │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  4. LLM Reranking                                      │
│  - Send original query + all chunks to LLM            │
│  - Ask: "Rank these by relevance, return top 3"       │
│  - Use GPT-4o-mini (fast + cheap)                     │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  5. Context Injection                                  │
│  - Format top 3 chunks as context                     │
│  - Inject into system prompt                          │
│  - Generate final response                            │
└────────────────────────────────────────────────────────┘
```

---

## 🔍 Component Details

### 1. Query Expansion (Multi-Query)

**Goal:** Improve recall by searching with multiple phrasings of the same question.

**Implementation:**
```python
def generate_query_variants(original_query: str) -> list[str]:
    """Generate 3-5 semantically similar queries."""
    prompt = f"""
    Given this user question, generate 3 alternative phrasings
    that maintain the same semantic meaning but use different words.

    Original: {original_query}

    Return as JSON array: ["variant1", "variant2", "variant3"]
    """

    response = llm.invoke(prompt)
    variants = json.loads(response.content)

    # Always include original
    return [original_query] + variants
```

**Example:**
```python
query = "Quel est le délai de livraison ?"
variants = [
    "Quel est le délai de livraison ?",  # original
    "Combien de temps pour recevoir ma commande ?",
    "Délai d'expédition des colis",
    "Livraison rapide disponible ?"
]
```

**Why it works:**
- User might phrase question differently than documentation
- Increases chance of finding relevant content
- Low cost (1 LLM call with cheap model)

---

### 2. Dense Vector Search (Qdrant)

**Collection Schema:**
```python
{
    "collection_name": "knowledge_base",
    "vectors": {
        "size": 1536,  # text-embedding-3-small dimension
        "distance": "Cosine"
    },
    "payload_schema": {
        "tenant_id": "keyword",    # for filtering
        "source_type": "keyword",  # 'document', 'website', 'faq'
        "source_id": "keyword",    # references documents.id or website_pages.id
        "content": "text",         # the actual text chunk
        "metadata": "json"         # additional info (title, url, etc.)
    }
}
```

**Search Implementation:**
```python
async def search_qdrant(
    query: str,
    tenant_id: str,
    top_k: int = 5
) -> list[dict]:
    """Search Qdrant with tenant filtering."""

    # Generate embedding
    embedding = await embed_text(query)

    # Search with filters
    results = qdrant_client.search(
        collection_name="knowledge_base",
        query_vector=embedding,
        limit=top_k,
        query_filter={
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}},
                {"key": "source_type", "match": {"any": ["document", "website"]}}
            ]
        }
    )

    return [
        {
            "id": hit.id,
            "content": hit.payload["content"],
            "score": hit.score,
            "source_type": hit.payload["source_type"],
            "metadata": hit.payload["metadata"]
        }
        for hit in results
    ]
```

**Multi-Query Search:**
```python
async def multi_query_search(
    queries: list[str],
    tenant_id: str
) -> list[dict]:
    """Search with multiple queries and merge results."""

    all_chunks = []

    # Search for each query variant
    for query in queries:
        chunks = await search_qdrant(query, tenant_id, top_k=5)
        all_chunks.extend(chunks)

    # Deduplicate by chunk ID
    unique_chunks = {chunk["id"]: chunk for chunk in all_chunks}

    # Sort by score (highest first)
    sorted_chunks = sorted(
        unique_chunks.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return sorted_chunks[:12]  # Keep top 12 for reranking
```

---

### 3. LLM-Based Reranking

**Goal:** Use LLM intelligence to pick most relevant chunks (better than similarity score alone).

**Why not use Cohere/Jina rerankers?**
- Cohere = 1000 free calls/month (good, but external dependency)
- Jina = requires API key, slower
- **LLM reranking = flexible, free (with OpenRouter), understands nuance**

**Implementation:**
```python
async def rerank_with_llm(
    original_query: str,
    chunks: list[dict],
    top_k: int = 3
) -> list[dict]:
    """Rerank chunks using LLM."""

    # Format chunks for LLM
    chunks_text = "\n\n".join([
        f"[{i}] {chunk['content'][:200]}..."  # Truncate for context
        for i, chunk in enumerate(chunks)
    ])

    prompt = f"""
    Given the user question and these text chunks, rank them by relevance.
    Return the indices of the top {top_k} most relevant chunks.

    Question: {original_query}

    Chunks:
    {chunks_text}

    Return ONLY a JSON array of indices: [0, 3, 5]
    """

    response = await llm.ainvoke(prompt)
    selected_indices = json.loads(response.content)

    return [chunks[i] for i in selected_indices[:top_k]]
```

**Alternative: Score-Based Reranking (simpler for MVP):**
```python
def rerank_by_score(chunks: list[dict], top_k: int = 3) -> list[dict]:
    """Simple reranking by similarity score."""
    return sorted(chunks, key=lambda x: x["score"], reverse=True)[:top_k]
```

**For hackathon: Use score-based first, upgrade to LLM if time permits.**

---

### 4. Context Injection

**Format retrieved chunks for LLM:**
```python
def format_rag_context(chunks: list[dict]) -> str:
    """Format chunks into context string."""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["metadata"].get("source_url") or chunk["metadata"].get("filename")
        context_parts.append(f"""
Source {i}: {source}
{chunk["content"]}
        """.strip())

    return "\n\n---\n\n".join(context_parts)
```

**System Prompt Template:**
```python
SYSTEM_PROMPT = """
You are an AI customer support assistant for {business_name}.

Use the following information to answer the customer's question:

{rag_context}

If the information is not in the context, say you don't know and offer to escalate to a human agent.

Always be helpful, concise, and friendly.
"""
```

**Example:**
```
You are an AI customer support assistant for Ma Boutique.

Use the following information to answer the customer's question:

---

Source 1: https://ma-boutique.com/livraison
Nous livrons en France métropolitaine sous 3 à 5 jours ouvrés.
La livraison est gratuite à partir de 50€ d'achat.

---

Source 2: politique_retours.pdf
Les retours sont acceptés sous 30 jours. Le produit doit être
dans son emballage d'origine avec l'étiquette.

---

If the information is not in the context, say you don't know...
```

---

## 🌐 Website Ingestion with Crawl4AI

**Why Crawl4AI > BeautifulSoup?**
- ✅ Handles JavaScript-rendered content (SPA support)
- ✅ Automatic content extraction (main content vs ads/navbars)
- ✅ Async crawling (faster for multiple pages)
- ✅ Built-in rate limiting
- ✅ Markdown output (cleaner than raw HTML)

**Installation:**
```bash
pip install crawl4ai
```

**Basic Usage:**
```python
from crawl4ai import AsyncWebCrawler

async def crawl_website(base_url: str, max_pages: int = 50) -> list[dict]:
    """Crawl website and extract content."""

    async with AsyncWebCrawler() as crawler:
        # Crawl starting page
        result = await crawler.arun(
            url=base_url,
            word_count_threshold=50,  # Min words per page
            excluded_tags=['nav', 'footer', 'aside'],  # Skip navigation
            exclude_external_links=True
        )

        pages = [{
            "url": result.url,
            "title": result.title,
            "content": result.markdown,  # Clean markdown content
            "links": result.internal_links
        }]

        # Crawl internal links (up to max_pages)
        visited = {base_url}
        to_visit = list(result.internal_links)[:max_pages]

        for link in to_visit:
            if link in visited:
                continue

            visited.add(link)

            try:
                result = await crawler.arun(url=link)
                pages.append({
                    "url": result.url,
                    "title": result.title,
                    "content": result.markdown,
                    "links": result.internal_links
                })
            except Exception as e:
                print(f"Failed to crawl {link}: {e}")
                continue

        return pages
```

**Integration with Supabase + Qdrant:**
```python
async def ingest_website(
    tenant_id: str,
    base_url: str,
    max_pages: int = 50
):
    """Full pipeline: crawl → store → embed → index."""

    # 1. Crawl website
    pages = await crawl_website(base_url, max_pages)

    # 2. Store in Supabase
    website_source = supabase.table("website_sources").insert({
        "tenant_id": tenant_id,
        "base_url": base_url,
        "max_pages": max_pages,
        "status": "crawling"
    }).execute()

    for page in pages:
        # Store page
        db_page = supabase.table("website_pages").insert({
            "website_source_id": website_source.data[0]["id"],
            "tenant_id": tenant_id,
            "url": page["url"],
            "title": page["title"],
            "content": page["content"]
        }).execute()

        # 3. Chunk content
        chunks = chunk_text(page["content"], chunk_size=500, overlap=50)

        for i, chunk in enumerate(chunks):
            # Store chunk in DB
            db_chunk = supabase.table("knowledge_chunks").insert({
                "tenant_id": tenant_id,
                "source_type": "website",
                "source_id": db_page.data[0]["id"],
                "content": chunk,
                "metadata": {
                    "chunk_index": i,
                    "parent_url": page["url"],
                    "parent_title": page["title"]
                }
            }).execute()

            # 4. Generate embedding
            embedding = await embed_text(chunk)

            # 5. Index in Qdrant
            qdrant_client.upsert(
                collection_name="knowledge_base",
                points=[{
                    "id": db_chunk.data[0]["id"],
                    "vector": embedding,
                    "payload": {
                        "tenant_id": tenant_id,
                        "source_type": "website",
                        "source_id": db_page.data[0]["id"],
                        "content": chunk,
                        "metadata": {
                            "url": page["url"],
                            "title": page["title"],
                            "chunk_index": i
                        }
                    }
                }]
            )

    # Update status
    supabase.table("website_sources").update({
        "status": "completed",
        "pages_crawled": len(pages),
        "last_crawled_at": "NOW()"
    }).eq("id", website_source.data[0]["id"]).execute()
```

---

## 📄 Document Ingestion (PDF/Word)

**Libraries:**
```bash
pip install pypdf  # for PDFs
pip install python-docx  # for Word docs
```

**PDF Extraction:**
```python
from pypdf import PdfReader

def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text
```

**Word Extraction:**
```python
from docx import Document

def extract_docx_text(file_path: str) -> str:
    """Extract text from Word document."""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])
```

**Full Upload Flow:**
```python
async def upload_document(
    tenant_id: str,
    file: UploadFile
):
    """Upload document → extract → chunk → embed → index."""

    # 1. Save to Supabase Storage
    file_path = f"tenants/{tenant_id}/documents/{file.filename}"
    supabase.storage.from_("documents").upload(file_path, file.file)

    # 2. Store metadata in DB
    db_doc = supabase.table("documents").insert({
        "tenant_id": tenant_id,
        "filename": file.filename,
        "file_path": file_path,
        "file_size": file.size,
        "mime_type": file.content_type,
        "status": "processing"
    }).execute()

    # 3. Extract text
    if file.content_type == "application/pdf":
        text = extract_pdf_text(file.file)
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_docx_text(file.file)
    else:
        raise ValueError(f"Unsupported file type: {file.content_type}")

    # 4. Chunk + embed + index (same as website ingestion)
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    for i, chunk in enumerate(chunks):
        # ... (same as website ingestion)
        pass

    # 5. Update status
    supabase.table("documents").update({
        "status": "processed",
        "chunk_count": len(chunks)
    }).eq("id", db_doc.data[0]["id"]).execute()
```

---

## ⚙️ Chunking Strategy

**Goal:** Split long documents into digestible chunks for embedding.

**Parameters:**
- `chunk_size`: 500 characters (~ 125 tokens)
- `overlap`: 50 characters (preserve context across chunks)

**Implementation:**
```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Only add non-empty chunks
        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks
```

**Advanced (sentence-aware chunking):**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]  # Split on paragraphs first, then sentences
)

chunks = splitter.split_text(text)
```

---

## 🚀 End-to-End RAG Flow

**User asks: "Quel est le délai de livraison ?"**

```python
# 1. Generate query variants
queries = generate_query_variants("Quel est le délai de livraison ?")
# → ["Quel est le délai de livraison ?", "Combien de temps pour recevoir...", ...]

# 2. Multi-query search
chunks = await multi_query_search(queries, tenant_id="ma-boutique")
# → 12 unique chunks from Qdrant

# 3. Rerank (score-based for MVP)
top_chunks = rerank_by_score(chunks, top_k=3)
# → Top 3 most relevant chunks

# 4. Format context
context = format_rag_context(top_chunks)

# 5. Generate response
system_prompt = SYSTEM_PROMPT.format(
    business_name="Ma Boutique",
    rag_context=context
)

response = llm.invoke([
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Quel est le délai de livraison ?"}
])

# → "Le délai de livraison est de 3 à 5 jours ouvrés en France métropolitaine..."
```

---

## 🎯 Performance Optimization

### For Hackathon (MVP)
- ✅ Dense embeddings only (skip hybrid search)
- ✅ Score-based reranking (skip LLM reranking)
- ✅ Single Qdrant collection with filters
- ✅ Crawl max 10-20 pages per website

### For Production
- ⚡ Add sparse vectors (BM25) for hybrid search
- ⚡ LLM reranking with GPT-4o-mini
- ⚡ Separate Qdrant collections per tenant (if >100 tenants)
- ⚡ Cache embeddings (Redis) for frequently asked questions
- ⚡ Batch processing for document uploads

---

## 📊 Metrics to Track

```python
rag_metrics = {
    "query_time_ms": 150,  # Total time for RAG pipeline
    "chunks_retrieved": 12,
    "chunks_used": 3,
    "sources": ["website_page_A", "document_B"],
    "rerank_method": "score_based",  # or "llm"
    "confidence_score": 0.89
}
```

Store in `conversation_messages.metadata` for analysis.

---

## 🔗 Related Documentation
- [Project Architecture](./project_architecture.md)
- [Database Schema](./database_schema.md)
- [Adding RAG Sources SOP](../SOP/adding_rag_sources.md)
