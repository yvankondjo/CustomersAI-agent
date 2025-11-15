import asyncio
import logging
from typing import Optional
from app.workers.ingest_document import process_and_store_document
from app.workers.ingest_website import process_and_store_website, crawl_and_process_website

logger = logging.getLogger(__name__)

def run_async_task(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def process_document_task(document_id: str, user_id: str):
    try:
        logger.info(f"Starting document processing task: {document_id} for user: {user_id}")
        run_async_task(process_and_store_document(document_id, user_id))
        logger.info(f"Completed document processing task: {document_id}")
        return {"status": "success", "document_id": document_id}
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        raise

def process_website_task(url: str, user_id: str, max_pages: int = 50, website_page_id: Optional[str] = None):
    try:
        logger.info(f"Starting website processing task: {url} for user: {user_id}, max_pages: {max_pages}")
        run_async_task(crawl_and_process_website(url, user_id, max_pages, website_page_id))
        logger.info(f"Completed website processing task: {url}")
        return {"status": "success", "url": url, "max_pages": max_pages}
    except Exception as e:
        logger.error(f"Error processing website {url}: {e}", exc_info=True)
        raise

