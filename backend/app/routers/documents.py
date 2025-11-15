from fastapi import APIRouter, HTTPException, UploadFile, File
import logging
import uuid
from app.db.session import get_db
from app.core.constants import DEFAULT_USER_ID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        db = get_db()
        
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.md']
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        document_id = str(uuid.uuid4())
        bucket_id = "documents"
        object_name = f"{DEFAULT_USER_ID}/{document_id}{file_ext}"
        
        try:
            db.storage.from_(bucket_id).upload(
                object_name,
                file_content,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
        except Exception as e:
            logger.error(f"Error uploading to storage: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
        
        doc_data = {
            "id": document_id,
            "filename": file.filename,
            "file_path": f"{bucket_id}/{object_name}",
            "file_size": file_size,
            "mime_type": file.content_type or "application/octet-stream",
            "status": "pending"
        }
        
        try:
            result = db.table("documents").insert(doc_data).execute()
            if result.data:
                logger.info(f"Document uploaded: {document_id}")
                return {
                    "document_id": document_id,
                    "filename": file.filename,
                    "size": file_size,
                    "status": "uploaded"
                }
            else:
                knowledge_doc_data = {
                    "id": document_id,
                    "title": file.filename,
                    "bucket_id": bucket_id,
                    "object_name": object_name,
                    "status": "pending"
                }
                db.table("knowledge_documents").insert(knowledge_doc_data).execute()
                return {
                    "document_id": document_id,
                    "filename": file.filename,
                    "size": file_size,
                    "status": "uploaded"
                }
        except Exception as e:
            logger.error(f"Error saving document metadata: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save document metadata: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

