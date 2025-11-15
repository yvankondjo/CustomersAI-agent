from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
from app.db.session import get_db
from supabase import Client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

class ConversationMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime

class Conversation(BaseModel):
    id: str
    user_id: str
    platform: str
    platform_user_id: Optional[str] = None
    platform_username: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    unread_count: int = 0

class ConversationDetail(BaseModel):
    conversation: Conversation
    messages: List[ConversationMessage]

@router.get("/", response_model=List[Conversation])
async def get_conversations(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Client = Depends(get_db)
):
    """Récupérer toutes les conversations"""
    try:
        query = db.table("conversations").select("*")
        
        if platform and platform != "all":
            query = query.eq("channel", platform)
        
        if status and status != "all":
            query = query.eq("status", status)
        
        query = query.order("last_message_at", desc=True).order("created_at", desc=True).limit(limit)
        
        result = query.execute()
        logger.info(f"Found {len(result.data or [])} conversations (platform={platform}, status={status})")
        
        if not result.data:
            logger.warning("No conversations found in database")
            return []
        
        logger.debug(f"Sample conversation data: {result.data[0] if result.data else 'None'}")
        
        conversations = []
        for idx, conv_data in enumerate(result.data):
            try:
                logger.debug(f"Processing conversation {idx+1}/{len(result.data)}: {conv_data.get('id')}")
                
                last_msg_result = db.table("conversation_messages").select("content").eq(
                    "conversation_id", conv_data["id"]
                ).order("created_at", desc=True).limit(1).execute()
                
                last_message = None
                if last_msg_result.data:
                    last_message = last_msg_result.data[0]["content"]
                
                metadata = conv_data.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                customer_identifier = metadata.get("customer_identifier")
                
                created_at_str = conv_data.get("created_at")
                if isinstance(created_at_str, str):
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning(f"Invalid created_at format: {created_at_str}")
                        created_at = datetime.now()
                elif created_at_str:
                    created_at = created_at_str
                else:
                    created_at = datetime.now()
                
                updated_at_str = conv_data.get("updated_at") or conv_data.get("last_message_at") or created_at_str
                if isinstance(updated_at_str, str):
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning(f"Invalid updated_at format: {updated_at_str}")
                        updated_at = created_at
                elif updated_at_str:
                    updated_at = updated_at_str
                else:
                    updated_at = created_at
                
                conversation = Conversation(
                    id=str(conv_data["id"]),
                    user_id=str(conv_data.get("user_id", "unknown")),
                    platform=conv_data.get("channel", "unknown"),
                    platform_user_id=customer_identifier,
                    platform_username=metadata.get("customer_name") or metadata.get("account_username") or (f"User {customer_identifier[:8]}" if customer_identifier else "Unknown"),
                    status=conv_data.get("status", "open"),
                    created_at=created_at,
                    updated_at=updated_at,
                    last_message=last_message,
                    unread_count=0
                )
                conversations.append(conversation)
                logger.debug(f"Successfully processed conversation {conv_data.get('id')}")
            except Exception as e:
                logger.error(f"Error processing conversation {conv_data.get('id', 'unknown')}: {e}", exc_info=True)
                continue
        
        logger.info(f"Returning {len(conversations)} conversations")
        return conversations
    
    except Exception as e:
        logger.error(f"Error getting conversations: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error getting conversations: {str(e)}")

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: str,
    db: Client = Depends(get_db)
):
    """Récupérer les détails d'une conversation avec ses messages"""
    try:
        # Récupérer la conversation
        conv_result = db.table("conversations").select("*").eq("id", conversation_id).execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv_data = conv_result.data[0]
        
        messages_result = db.table("conversation_messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at", asc=True).execute()
        
        messages = []
        for msg_data in messages_result.data:
            created_at = msg_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            message = ConversationMessage(
                id=msg_data["id"],
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=created_at
            )
            messages.append(message)
        
        metadata = conv_data.get("metadata", {})
        customer_identifier = metadata.get("customer_identifier")
        
        created_at_str = conv_data.get("created_at")
        if isinstance(created_at_str, str):
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at = created_at_str or datetime.now()
        
        updated_at_str = conv_data.get("updated_at") or conv_data.get("last_message_at") or created_at_str
        if isinstance(updated_at_str, str):
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        else:
            updated_at = updated_at_str or created_at
        
        conversation = Conversation(
            id=conv_data["id"],
            user_id=conv_data["user_id"],
            platform=conv_data.get("channel", "unknown"),
            platform_user_id=customer_identifier,
            platform_username=metadata.get("customer_name") or metadata.get("account_username") or (f"User {customer_identifier[:8]}" if customer_identifier else "Unknown"),
            status=conv_data.get("status", "open"),
            created_at=created_at,
            updated_at=updated_at
        )
        
        return ConversationDetail(conversation=conversation, messages=messages)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation detail: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting conversation detail: {str(e)}")

@router.post("/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: str,
    message: dict,
    db: Client = Depends(get_db)
):
    """Répondre à une conversation"""
    try:
        # Vérifier que la conversation existe
        conv_result = db.table("conversations").select("*").eq("id", conversation_id).execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Ajouter le message de réponse
        new_message = {
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": message.get("content", ""),
            "created_at": datetime.utcnow().isoformat()
        }
        
        db.table("conversation_messages").insert(new_message).execute()
        
        # Mettre à jour le timestamp de la conversation
        db.table("conversations").update({
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).execute()
        
        return {"status": "success", "message": "Reply sent"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replying to conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error replying to conversation: {str(e)}")

@router.patch("/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: str,
    status_update: dict,
    db: Client = Depends(get_db)
):
    """Mettre à jour le statut d'une conversation"""
    try:
        new_status = status_update.get("status")
        if new_status not in ["active", "resolved", "escalated"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        result = db.table("conversations").update({
            "status": new_status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"status": "success", "message": f"Conversation status updated to {new_status}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation status: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating conversation status: {str(e)}")
