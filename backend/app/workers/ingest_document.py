import os
import asyncio
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import get_settings
from app.db.session import get_db
from app.services.ingest_helper import (
    parse_bytes_by_ext,
    chunk_text,
    get_title_and_summary,
    get_embedding
)

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

async def process_chunk(chunk: str, chunk_number: int, document_id: str, url: str = "") -> ProcessedChunk:
    extracted = await get_title_and_summary(chunk, url)
    embedding = await get_embedding(chunk)
    
    metadata = {
        "source": "document",
        "document_id": document_id,
        "chunk_size": len(chunk),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return ProcessedChunk(
        url=url or f"document://{document_id}",
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

async def process_and_store_document(document_id: str, user_id: str):
    db = get_db()

    doc_result = db.table("documents").select(
        "id,filename,file_path,status"
    ).eq("id", document_id).single().execute()

    if not doc_result.data:
        raise RuntimeError("Document introuvable")

    doc = doc_result.data
    doc_user_id = user_id
    file_path = doc.get("file_path")

    db.table("documents").update({"status": "processing"}).eq("id", document_id).execute()

    try:
        if file_path:
            path_parts = file_path.split("/")
            if len(path_parts) >= 2:
                bucket_id = path_parts[0]
                object_name = "/".join(path_parts[1:])
                data = db.storage.from_(bucket_id).download(object_name)
            else:
                raise RuntimeError(f"Format de file_path invalide: {file_path}")
        else:
            raise RuntimeError("file_path manquant")

        content = parse_bytes_by_ext(data, os.path.splitext(doc["filename"])[1].lower())
        chunks = chunk_text(content)

        init_qdrant_collection()

        tasks = [
            process_chunk(chunk, i, document_id, f"document://{document_id}")
            for i, chunk in enumerate(chunks)
        ]
        processed_chunks = await asyncio.gather(*tasks)

        insert_tasks = [
            insert_chunk_to_qdrant(chunk, doc_user_id)
            for chunk in processed_chunks
        ]
        await asyncio.gather(*insert_tasks)

        db.table("documents").update({
            "status": "processed",
            "chunk_count": len(chunks)
        }).eq("id", document_id).execute()

        logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        db.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        raise

