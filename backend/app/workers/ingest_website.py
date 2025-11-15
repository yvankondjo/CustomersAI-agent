import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import get_settings
from app.services.ingest_helper import (
    chunk_text,
    get_title_and_summary,
    get_embedding
)

try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.models import CrawlResult
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Crawl4AI not available. Install with: pip install crawl4ai")

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

def get_qdrant_client() -> QdrantClient:
    if settings.QDRANT_API_KEY:
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    return QdrantClient(url=settings.QDRANT_URL)

def init_qdrant_collection(collection_name: str = "knowledge_base"):
    qdrant = get_qdrant_client()
    try:
        collection_info = qdrant.get_collection(collection_name)
        logger.info(f"Collection {collection_name} already exists with size {collection_info.config.params.vectors.size}")
    except Exception:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Created collection {collection_name} with size 1536")

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    extracted = await get_title_and_summary(chunk, url)
    embedding = await get_embedding(chunk)
    
    metadata = {
        "source": "website",
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk,
        metadata=metadata,
        embedding=embedding
    )

async def insert_chunk_to_qdrant(chunk: ProcessedChunk, user_id: str, collection_name: str = "knowledge_base"):
    qdrant = get_qdrant_client()
    try:
        import hashlib
        point_id_str = f"{user_id}_{chunk.url}_{chunk.chunk_number}"
        point_id = int(hashlib.md5(point_id_str.encode()).hexdigest()[:15], 16) % (2**63)
        point = PointStruct(
            id=point_id,
            vector=chunk.embedding,
            payload={
                "user_id": user_id,
                "url": chunk.url,
                "chunk_number": chunk.chunk_number,
                "title": chunk.title,
                "summary": chunk.summary,
                "content": chunk.content,
                "metadata": chunk.metadata
            }
        )
        qdrant.upsert(
            collection_name=collection_name,
            points=[point]
        )
        logger.info(f"Inserted chunk {chunk.chunk_number} for {chunk.url} (user: {user_id})")
    except Exception as e:
        logger.error(f"Error inserting chunk to Qdrant: {e}")
        raise

def extract_title_from_result(result) -> str:
    title = "Untitled"
    try:
        title = getattr(result, 'title', None) or title
    except AttributeError:
        pass
    try:
        metadata = getattr(result, 'metadata', None)
        if metadata and isinstance(metadata, dict):
            title = metadata.get('title', title)
    except (AttributeError, TypeError):
        pass
    return title

async def process_and_store_website(url: str, markdown: str, user_id: str, title: str = "Untitled", website_page_id: str = None, website_source_id: str = None):
    chunks = chunk_text(markdown)
    
    init_qdrant_collection()
    
    tasks = [
        process_chunk(chunk, i, url)
        for i, chunk in enumerate(chunks)
    ]
    processed_chunks = await asyncio.gather(*tasks)
    
    insert_tasks = [
        insert_chunk_to_qdrant(chunk, user_id)
        for chunk in processed_chunks
    ]
    await asyncio.gather(*insert_tasks)
    
    from app.db.session import get_db
    db = get_db()
    
    try:
        if website_page_id:
            update_result = db.table("website_pages").update({
                "chunk_count": len(chunks),
                "title": title,
                "content": markdown[:10000] if len(markdown) > 10000 else markdown
            }).eq("id", website_page_id).execute()
            logger.info(f"Updated website page {website_page_id} for {url}")
        else:
            existing_page = db.table("website_pages").select("id").eq("url", url).execute()
            if existing_page.data and len(existing_page.data) > 0:
                update_result = db.table("website_pages").update({
                    "chunk_count": len(chunks),
                    "title": title,
                    "content": markdown[:10000] if len(markdown) > 10000 else markdown
                }).eq("id", existing_page.data[0]["id"]).execute()
                logger.info(f"Updated existing website page for {url}")
            else:
                if not website_source_id:
                    raise ValueError("website_source_id is required to create a new website page")
                
                insert_result = db.table("website_pages").insert({
                    "website_source_id": website_source_id,
                    "url": url,
                    "title": title,
                    "content": markdown[:10000] if len(markdown) > 10000 else markdown,
                    "chunk_count": len(chunks)
                }).execute()
                logger.info(f"Created new website page for {url} with {len(chunks)} chunks")
    except Exception as e:
        logger.error(f"Error saving website page to database: {e}", exc_info=True)
        raise
    
    logger.info(f"Successfully processed website {url} with {len(processed_chunks)} chunks")

async def crawl_and_process_website(base_url: str, user_id: str, max_pages: int = 50, website_page_id: Optional[str] = None):
    if not CRAWL4AI_AVAILABLE:
        raise RuntimeError("Crawl4AI is not installed. Install with: pip install crawl4ai")
    
    from app.db.session import get_db
    from app.core.constants import DEFAULT_USER_ID
    from urllib.parse import urlparse
    
    db = get_db()
    
    parsed_base = urlparse(base_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    website_source_id = None
    if website_page_id:
        existing_page = db.table("website_pages").select("website_source_id").eq("id", website_page_id).execute()
        if existing_page.data and existing_page.data[0].get("website_source_id"):
            website_source_id = existing_page.data[0]["website_source_id"]
    
    if not website_source_id:
        existing_source = db.table("website_sources").select("id").eq("base_url", base_domain).execute()
        if existing_source.data and len(existing_source.data) > 0:
            website_source_id = existing_source.data[0]["id"]
            db.table("website_sources").update({
                "status": "crawling",
                "max_pages": max_pages
            }).eq("id", website_source_id).execute()
        else:
            new_source = db.table("website_sources").insert({
                "base_url": base_domain,
                "max_pages": max_pages,
                "status": "crawling",
                "crawl_frequency": "manual"
            }).execute()
            if new_source.data:
                website_source_id = new_source.data[0]["id"]
            else:
                raise RuntimeError("Failed to create website_source")
    
    logger.info(f"Starting crawl for {base_url} (max_pages: {max_pages}, source_id: {website_source_id})")
    async with AsyncWebCrawler() as crawler:
        visited = set()
        pages_to_process = []
        to_visit = [base_url]
        
        while to_visit and len(pages_to_process) < max_pages:
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
            
            try:
                logger.info(f"Crawling {current_url} ({len(pages_to_process)}/{max_pages} pages)")
                result = await crawler.arun(
                    url=current_url,
                    word_count_threshold=50,
                    excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style'],
                    exclude_external_links=True
                )
                
                if result.success and result.markdown:
                    pages_to_process.append({
                        "url": result.url,
                        "title": extract_title_from_result(result),
                        "content": result.markdown
                    })
                    visited.add(result.url)
                    
                    internal_links = []
                    try:
                        if hasattr(result, 'internal_links') and result.internal_links:
                            if isinstance(result.internal_links, (list, set)):
                                internal_links = list(result.internal_links)
                            elif isinstance(result.internal_links, dict):
                                internal_links = list(result.internal_links.keys()) if result.internal_links else []
                    except Exception as e:
                        logger.warning(f"Error extracting internal links: {e}")
                    
                    for link in internal_links:
                        if link not in visited and link not in to_visit and len(pages_to_process) < max_pages:
                            parsed_base = urlparse(base_url)
                            parsed_link = urlparse(link)
                            
                            if parsed_link.netloc == parsed_base.netloc:
                                full_link = link
                            elif not parsed_link.netloc:
                                if link.startswith('/'):
                                    full_link = f"{parsed_base.scheme}://{parsed_base.netloc}{link}"
                                else:
                                    full_link = f"{parsed_base.scheme}://{parsed_base.netloc}/{link}"
                            else:
                                continue
                            
                            if full_link not in visited and full_link not in to_visit:
                                to_visit.append(full_link)
                                logger.debug(f"Added link to queue: {full_link}")
                else:
                    logger.warning(f"Failed to crawl {current_url}: success={result.success}")
            except Exception as e:
                logger.warning(f"Error crawling {current_url}: {e}")
                continue
        
        logger.info(f"Crawled {len(pages_to_process)} pages from {base_url}")
        
        total_chunks = 0
        for i, page in enumerate(pages_to_process):
            current_page_id = website_page_id if i == 0 and website_page_id else None
            
            await process_and_store_website(
                page["url"], 
                page["content"], 
                user_id, 
                page["title"],
                current_page_id,
                website_source_id
            )
            chunks = chunk_text(page["content"])
            total_chunks += len(chunks)
        
        db.table("website_sources").update({
            "status": "completed",
            "pages_crawled": len(pages_to_process),
            "last_crawled_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", website_source_id).execute()
        
        logger.info(f"Successfully crawled and processed {len(pages_to_process)} pages with {total_chunks} total chunks")
        return {"pages_crawled": len(pages_to_process), "total_chunks": total_chunks}

