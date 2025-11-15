from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
from app.services.rag_agent import create_rag_agent
from app.services.supabase_client import supabase_service
from app.core.constants import DEFAULT_USER_ID
from app.db.session import get_db
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/playground", tags=["playground"])

class PlaygroundMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None

class PlaygroundResponse(BaseModel):
    response: str
    conversation_id: str

def is_valid_uuid(uuid_string):
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

@router.post("/message", response_model=PlaygroundResponse)
async def playground_message(message: PlaygroundMessage):
    conversation_id = None
    try:
        db = get_db()
        
        conversation_id = message.conversation_id
        
        if conversation_id and is_valid_uuid(conversation_id):
            try:
                conv_result = db.table("conversations").select("*").eq("id", conversation_id).execute()
                if not conv_result.data:
                    conversation_id = None
            except Exception as e:
                logger.warning(f"Error checking conversation {conversation_id}: {e}")
                conversation_id = None
        else:
            conversation_id = None
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            db.table("conversations").insert({
                "id": conversation_id,
                "user_id": DEFAULT_USER_ID,
                "channel": "playground",
                "status": "open",
                "last_message_at": datetime.utcnow().isoformat(),
                "metadata": {"source": "playground", "session_id": str(uuid.uuid4())}
            }).execute()
            logger.info(f"✅ Created new conversation {conversation_id} for playground/web widget")
        
        try:
            await supabase_service.save_message(
                conversation_id=conversation_id,
                role="user",
                content=message.content,
                metadata={"source": "playground"}
            )
            logger.info(f"✅ Saved user message to conversation {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save user message: {e}", exc_info=True)
        
        agent = create_rag_agent(
            user_id=DEFAULT_USER_ID,
            conversation_id=conversation_id,
            test_mode=False,
            checkpointer=None
        )
        
        result = await agent.process_message(message.content)
        response_text = result.get("response", "No response generated")
        
        try:
            await supabase_service.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
                metadata={
                    "source": "playground",
                    "escalated": result.get("escalated", False),
                    "sources_count": len(result.get("sources", []))
                }
            )
            logger.info(f"✅ Saved assistant message to conversation {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save assistant message: {e}", exc_info=True)
        
        try:
            timestamp = datetime.utcnow().isoformat()
            db.table("conversations").update({
                "updated_at": timestamp,
                "last_message_at": timestamp
            }).eq("id", conversation_id).execute()
        except Exception as e:
            logger.error(f"❌ Failed to update conversation timestamp: {e}", exc_info=True)
        
        return PlaygroundResponse(
            response=response_text,
            conversation_id=conversation_id
        )
    except Exception as e:
        logger.error(f"❌ Error in playground: {e}", exc_info=True)
        if conversation_id:
            try:
                await supabase_service.save_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=f"Erreur lors du traitement: {str(e)}",
                    metadata={"source": "playground", "error": True}
                )
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

