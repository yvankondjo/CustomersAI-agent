from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import uuid
from app.db.session import get_db
from app.core.constants import DEFAULT_USER_ID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/faq", tags=["faq"])

class FAQCreate(BaseModel):
    question: str
    variants: List[str] = []
    answer: str
    category: Optional[str] = None

class FAQUpdate(BaseModel):
    question: Optional[str] = None
    variants: Optional[List[str]] = None
    answer: Optional[str] = None
    category: Optional[str] = None

class FAQResponse(BaseModel):
    id: str
    question: str
    variants: List[str]
    answer: str
    category: Optional[str]
    created_at: str
    updated_at: str

@router.post("", response_model=FAQResponse)
async def create_faq(faq: FAQCreate):
    try:
        db = get_db()
        faq_id = str(uuid.uuid4())

        faq_data = {
            "id": faq_id,
            "user_id": DEFAULT_USER_ID,
            "question": faq.question,
            "variants": faq.variants,
            "answer": faq.answer,
            "category": faq.category or "general"
        }

        result = db.table("faqs").insert(faq_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create FAQ")

        logger.info(f"Created FAQ {faq_id}")
        return FAQResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating FAQ: {str(e)}")

@router.get("", response_model=List[FAQResponse])
async def list_faqs():
    try:
        db = get_db()
        result = db.table("faqs").select("*").eq("user_id", DEFAULT_USER_ID).order("created_at", desc=True).execute()
        
        return [FAQResponse(**item) for item in result.data]
    except Exception as e:
        logger.error(f"Error listing FAQs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing FAQs: {str(e)}")

@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq(faq_id: str):
    try:
        db = get_db()
        result = db.table("faqs").select("*").eq("id", faq_id).eq("user_id", DEFAULT_USER_ID).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        return FAQResponse(**result.data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting FAQ: {str(e)}")

@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(faq_id: str, faq: FAQUpdate):
    try:
        db = get_db()

        update_data = {}
        if faq.question is not None:
            update_data["question"] = faq.question
        if faq.variants is not None:
            update_data["variants"] = faq.variants
        if faq.answer is not None:
            update_data["answer"] = faq.answer
        if faq.category is not None:
            update_data["category"] = faq.category

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = db.table("faqs").update(update_data).eq("id", faq_id).eq("user_id", DEFAULT_USER_ID).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="FAQ not found")

        updated_faq = result.data[0]

        logger.info(f"Updated FAQ {faq_id}")
        return FAQResponse(**updated_faq)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating FAQ: {str(e)}")

@router.delete("/{faq_id}")
async def delete_faq(faq_id: str):
    try:
        db = get_db()
        result = db.table("faqs").delete().eq("id", faq_id).eq("user_id", DEFAULT_USER_ID).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="FAQ not found")

        logger.info(f"Deleted FAQ {faq_id}")
        return {"message": "FAQ deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting FAQ: {str(e)}")

