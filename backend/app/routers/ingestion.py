"""
Ingestion router using asyncio.create_task (No Redis required)
Compatible with Playwright/Crawl4AI on Windows
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import asyncio
import uuid

from app.db.session import get_db
from app.core.constants import DEFAULT_USER_ID
from app.workers.ingest_document import process_and_store_document
from app.workers.ingest_website import crawl_and_process_website

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


class DocumentIngestRequest(BaseModel):
    document_id: str


class WebsiteIngestRequest(BaseModel):
    url: str
    max_pages: int = 50
    website_page_id: Optional[str] = None


class IngestionResponse(BaseModel):
    status: str
    task_id: str
    message: str


# Background task wrapper with proper error handling
async def process_document_async(document_id: str, user_id: str, task_id: str):
    """Process document in background using shared event loop"""
    try:
        logger.info(f"[Task {task_id}] 📄 Starting document processing: {document_id}")
        await process_and_store_document(document_id, user_id)
        logger.info(f"[Task {task_id}] ✅ Document processing completed: {document_id}")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Error processing document {document_id}: {e}", exc_info=True)


async def process_website_async(url: str, user_id: str, max_pages: int, website_page_id: Optional[str], task_id: str):
    """Process website in background using shared event loop"""
    try:
        logger.info(f"[Task {task_id}] 🌐 Starting website crawl: {url} (max_pages: {max_pages})")
        result = await crawl_and_process_website(url, user_id, max_pages, website_page_id)
        logger.info(f"[Task {task_id}] ✅ Website crawl completed: {url} - {result}")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Error processing website {url}: {e}", exc_info=True)


@router.post("/document", response_model=IngestionResponse)
async def ingest_document(request: DocumentIngestRequest):
    """
    Ingest a document in the background using asyncio.create_task
    No Redis required! Uses FastAPI's main event loop.
    """
    try:
        # Verify document exists
        db = get_db()
        doc_result = db.table("documents").select("id").eq("id", request.document_id).single().execute()
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]

        # Launch background task using asyncio.create_task (shares main event loop)
        asyncio.create_task(
            process_document_async(
                document_id=request.document_id,
                user_id=DEFAULT_USER_ID,
                task_id=task_id
            )
        )

        logger.info(f"📄 Launched document ingestion task {task_id} for document {request.document_id}")

        return IngestionResponse(
            status="processing",
            task_id=task_id,
            message=f"Document ingestion started in background"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching document ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error launching document ingestion: {str(e)}")


@router.post("/website", response_model=IngestionResponse)
async def ingest_website(request: WebsiteIngestRequest):
    """
    Crawl and ingest a website in the background using asyncio.create_task
    No Redis required! Uses FastAPI's main event loop (compatible with Playwright).
    """
    try:
        # Validate max_pages
        if request.max_pages < 1 or request.max_pages > 100:
            raise HTTPException(status_code=400, detail="max_pages must be between 1 and 100")

        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]

        # Launch background task using asyncio.create_task (shares main event loop)
        # This is critical for Playwright/Crawl4AI to work on Windows!
        asyncio.create_task(
            process_website_async(
                url=request.url,
                user_id=DEFAULT_USER_ID,
                max_pages=request.max_pages,
                website_page_id=request.website_page_id,
                task_id=task_id
            )
        )

        logger.info(f"🌐 Launched website ingestion task {task_id} for URL {request.url} (max_pages: {request.max_pages})")

        return IngestionResponse(
            status="processing",
            task_id=task_id,
            message=f"Website crawl started in background (max {request.max_pages} pages)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching website ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error launching website ingestion: {str(e)}")
