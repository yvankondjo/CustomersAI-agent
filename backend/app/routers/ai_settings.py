from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging
from app.db.session import get_db
from app.core.constants import DEFAULT_USER_ID
from supabase import Client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-settings", tags=["ai-settings"])

class AISettingsCreate(BaseModel):
    model_name: str = Field(default="mistral-small-2506")
    system_prompt: str = Field(default="You are a helpful AI assistant.")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)

class AISettingsResponse(BaseModel):
    id: str
    user_id: str
    model_name: str
    system_prompt: str
    temperature: float
    max_tokens: int
    top_p: Optional[float]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    created_at: datetime
    updated_at: datetime

@router.get("/", response_model=AISettingsResponse)
async def get_ai_settings(
    user_id: str = DEFAULT_USER_ID,
    db: Client = Depends(get_db)
):
    """Récupérer les paramètres AI pour un utilisateur"""
    try:
        result = db.table("ai_settings").select("*").eq("user_id", user_id).execute()
        
        if not result.data:
            default_settings = {
                "user_id": user_id,
                "model_name": "mistral-small-2506",
                "system_prompt": "You are a helpful AI assistant specialized in customer support. Be friendly, professional, and concise.",
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            insert_result = db.table("ai_settings").insert(default_settings).execute()
            return AISettingsResponse(**insert_result.data[0])
        
        return AISettingsResponse(**result.data[0])
    
    except Exception as e:
        logger.error(f"Error getting AI settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting AI settings: {str(e)}")

@router.put("/", response_model=AISettingsResponse)
async def update_ai_settings(
    settings: AISettingsCreate,
    user_id: str = DEFAULT_USER_ID,
    db: Client = Depends(get_db)
):
    """Mettre à jour les paramètres AI pour un utilisateur"""
    try:
        update_data = settings.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = db.table("ai_settings").update(update_data).eq("user_id", user_id).execute()
        
        if not result.data:
            create_data = settings.dict()
            create_data["user_id"] = user_id
            insert_result = db.table("ai_settings").insert(create_data).execute()
            return AISettingsResponse(**insert_result.data[0])
        
        return AISettingsResponse(**result.data[0])
    
    except Exception as e:
        logger.error(f"Error updating AI settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating AI settings: {str(e)}")

@router.patch("/", response_model=AISettingsResponse)
async def patch_ai_settings(
    settings: AISettingsCreate,
    user_id: str = DEFAULT_USER_ID,
    db: Client = Depends(get_db)
):
    """Mettre à jour partiellement les paramètres AI"""
    try:
        update_data = settings.dict(exclude_unset=True, exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = db.table("ai_settings").update(update_data).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="AI settings not found")
        
        return AISettingsResponse(**result.data[0])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching AI settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error patching AI settings: {str(e)}")
