from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from urllib.parse import urlparse
from app.db.session import get_db
from app.core.constants import DEFAULT_USER_ID
from qdrant_client import QdrantClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

def get_qdrant_client():
    settings = get_settings()
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
    )

@router.get("/documents")
async def list_documents():
    try:
        db = get_db()

        documents_result = db.table("documents").select("*").order("created_at", desc=True).execute()

        return documents_result.data if documents_result.data else []
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        db = get_db()
        qdrant = get_qdrant_client()

        doc_result = db.table("documents").select("*").eq("id", document_id).single().execute()

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        db.table("documents").delete().eq("id", document_id).execute()
        
        try:
            qdrant.delete(
                collection_name="knowledge_base",
                points_selector={
                    "filter": {
                        "must": [
                            {"key": "user_id", "match": {"value": DEFAULT_USER_ID}},
                            {"key": "url", "match": {"value": f"document://{document_id}"}}
                        ]
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Error deleting from Qdrant: {e}")
        
        logger.info(f"Deleted document {document_id}")
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/websites")
async def list_websites():
    try:
        db = get_db()
        result = db.table("website_pages").select("*").order("created_at", desc=True).execute()
        
        logger.info(f"Found {len(result.data) if result.data else 0} website pages in database")
        
        if not result.data:
            logger.info("No website pages found, returning empty list")
            return []
        
        websites = {}
        for page in result.data:
            url = page.get("url", "")
            if not url:
                logger.warning(f"Skipping page with no URL: {page.get('id')}")
                continue
            
            try:
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
            except Exception as e:
                logger.warning(f"Error parsing URL {url}: {e}")
                base_url = url
            
            if base_url not in websites:
                websites[base_url] = {
                    "base_url": base_url,
                    "pages": [],
                    "total_pages": 0,
                    "total_chunks": 0
                }
            websites[base_url]["pages"].append(page)
            websites[base_url]["total_pages"] += 1
            websites[base_url]["total_chunks"] += page.get("chunk_count", 0) or 0
        
        result_list = list(websites.values())
        total_pages = sum(w['total_pages'] for w in result_list)
        logger.info(f"Returning {len(result_list)} websites with {total_pages} total pages")
        
        for website in result_list:
            logger.debug(f"Website {website['base_url']}: {website['total_pages']} pages, {website['total_chunks']} chunks")
            for page in website['pages']:
                logger.debug(f"  - Page: {page.get('url')} (chunks: {page.get('chunk_count', 0)})")
        
        return result_list
    except Exception as e:
        logger.error(f"Error listing websites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing websites: {str(e)}")

@router.delete("/websites/all")
async def delete_all_websites():
    try:
        db = get_db()
        qdrant = get_qdrant_client()
        
        pages_result = db.table("website_pages").select("id,url").execute()
        
        if pages_result.data:
            page_ids = [page["id"] for page in pages_result.data]
            urls = [page["url"] for page in pages_result.data]
            
            db.table("website_pages").delete().in_("id", page_ids).execute()
            
            try:
                for url in urls:
                    qdrant.delete(
                        collection_name="knowledge_base",
                        points_selector={
                            "filter": {
                                "must": [
                                    {"key": "user_id", "match": {"value": DEFAULT_USER_ID}},
                                    {"key": "url", "match": {"value": url}}
                                ]
                            }
                        }
                    )
            except Exception as e:
                logger.warning(f"Error deleting from Qdrant: {e}")
        
        logger.info(f"Deleted all websites for user {DEFAULT_USER_ID}")
        return {"message": f"Deleted {len(pages_result.data) if pages_result.data else 0} website pages"}
    except Exception as e:
        logger.error(f"Error deleting all websites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting all websites: {str(e)}")

@router.delete("/websites/{website_id}")
async def delete_website(website_id: str):
    try:
        db = get_db()
        qdrant = get_qdrant_client()
        
        page_result = db.table("website_pages").select("*").eq("id", website_id).single().execute()
        
        if not page_result.data:
            raise HTTPException(status_code=404, detail="Website page not found")
        
        url = page_result.data["url"]
        
        db.table("website_pages").delete().eq("id", website_id).execute()
        
        try:
            qdrant.delete(
                collection_name="knowledge_base",
                points_selector={
                    "filter": {
                        "must": [
                            {"key": "user_id", "match": {"value": DEFAULT_USER_ID}},
                            {"key": "url", "match": {"value": url}}
                        ]
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Error deleting from Qdrant: {e}")
        
        logger.info(f"Deleted website page {website_id}")
        return {"message": "Website page deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting website: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting website: {str(e)}")

