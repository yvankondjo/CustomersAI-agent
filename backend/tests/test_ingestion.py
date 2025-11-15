import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.workers.ingest_document import process_and_store_document
from app.workers.ingest_website import crawl_and_process_website, process_and_store_website
from app.workers.rq_workers import process_document_task, process_website_task

@pytest.fixture
def mock_db():
    db = Mock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "test-doc-id",
        "user_id": "test-user-id",
        "filename": "test.pdf",
        "file_path": "bucket/test.pdf",
        "status": "pending"
    }
    db.storage.from_.return_value.download.return_value = b"test pdf content"
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return db

@pytest.fixture
def mock_qdrant():
    qdrant = Mock()
    qdrant.get_collection.side_effect = Exception("Collection not found")
    qdrant.create_collection.return_value = None
    qdrant.upsert.return_value = None
    return qdrant

@pytest.mark.asyncio
async def test_process_document_basic():
    with patch("app.workers.ingest_document.get_db") as mock_get_db, \
         patch("app.workers.ingest_document.get_qdrant_client") as mock_qdrant, \
         patch("app.workers.ingest_document.chunk_text") as mock_chunk, \
         patch("app.workers.ingest_document.process_chunk") as mock_process, \
         patch("app.workers.ingest_document.insert_chunk_to_qdrant") as mock_insert:
        
        mock_db = Mock()
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-doc-id",
            "user_id": "test-user-id",
            "filename": "test.pdf",
            "file_path": "bucket/test.pdf"
        }
        mock_db.storage.from_.return_value.download.return_value = b"test content"
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        
        mock_get_db.return_value = mock_db
        
        mock_qdrant_client = Mock()
        mock_qdrant_client.get_collection.side_effect = Exception("Not found")
        mock_qdrant_client.create_collection.return_value = None
        mock_qdrant.return_value = mock_qdrant_client
        
        mock_chunk.return_value = ["chunk1", "chunk2"]
        
        from app.workers.ingest_document import ProcessedChunk
        mock_process.return_value = ProcessedChunk(
            url="document://test-doc-id",
            chunk_number=0,
            title="Test",
            summary="Test summary",
            content="chunk1",
            metadata={},
            embedding=[0.1] * 1536
        )
        mock_insert.return_value = None
        
        await process_and_store_document("test-doc-id", "test-user-id")
        
        assert mock_db.table.return_value.update.call_count >= 2

@pytest.mark.asyncio
async def test_process_website_basic():
    with patch("app.workers.ingest_website.get_qdrant_client") as mock_qdrant, \
         patch("app.workers.ingest_website.chunk_text") as mock_chunk, \
         patch("app.workers.ingest_website.process_chunk") as mock_process, \
         patch("app.workers.ingest_website.insert_chunk_to_qdrant") as mock_insert:
        
        mock_qdrant_client = Mock()
        mock_qdrant_client.get_collection.side_effect = Exception("Not found")
        mock_qdrant_client.create_collection.return_value = None
        mock_qdrant.return_value = mock_qdrant_client
        
        mock_chunk.return_value = ["chunk1"]
        
        from app.workers.ingest_website import ProcessedChunk
        mock_process.return_value = ProcessedChunk(
            url="https://example.com",
            chunk_number=0,
            title="Test",
            summary="Test summary",
            content="chunk1",
            metadata={},
            embedding=[0.1] * 1536
        )
        mock_insert.return_value = None
        
        await process_and_store_website("https://example.com", "# Test Content", "test-user-id")
        
        mock_insert.assert_called_once()

def test_process_document_task():
    with patch("app.workers.rq_workers.run_async_task") as mock_run:
        mock_run.return_value = {"status": "success"}
        
        result = process_document_task("test-doc-id", "test-user-id")
        
        assert result["status"] == "success"
        assert result["document_id"] == "test-doc-id"

def test_process_website_task():
    with patch("app.workers.rq_workers.run_async_task") as mock_run:
        mock_run.return_value = {"status": "success", "pages_crawled": 5}
        
        result = process_website_task("https://example.com", "test-user-id", max_pages=10)
        
        assert result["status"] == "success"
        assert result["url"] == "https://example.com"

@pytest.mark.asyncio
async def test_crawl_and_process_website():
    with patch("app.workers.ingest_website.AsyncWebCrawler") as mock_crawler_class, \
         patch("app.workers.ingest_website.process_and_store_website") as mock_process, \
         patch("app.workers.ingest_website.chunk_text") as mock_chunk:
        
        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "# Test Content"
        mock_result.url = "https://example.com"
        mock_result.title = "Test Page"
        mock_result.internal_links = []
        
        mock_crawler.arun.return_value = mock_result
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        mock_crawler_class.return_value = mock_crawler
        
        mock_process.return_value = None
        mock_chunk.return_value = ["chunk1"]
        
        result = await crawl_and_process_website("https://example.com", "test-user-id", max_pages=10)
        
        assert result["pages_crawled"] == 1
        assert result["total_chunks"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

