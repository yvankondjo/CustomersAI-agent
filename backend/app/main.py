"""FastAPI application for Customer AI Support Platform"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.models.schemas import MessageRequest, MessageResponse
from app.agents.router import create_agent
from app.services.supabase_client import supabase_service
from app.services.rag import rag_service

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("=€ Starting Customer AI Support Platform")

    # Initialize Qdrant collection (run once)
    try:
        rag_service.init_collection()
    except Exception as e:
        logger.warning(f"Qdrant init warning: {e}")

    yield

    # Shutdown
    logger.info("=K Shutting down Customer AI Support Platform")


# Create FastAPI app
app = FastAPI(
    title="Customer AI Support API",
    description="AI-powered customer support platform with Instagram + Web integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Customer AI Support API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT
    }


@app.post("/api/v1/support/message", response_model=MessageResponse)
async def handle_support_message(request: MessageRequest):
    """
    Main endpoint for handling customer support messages.

    This endpoint:
    1. Gets or creates conversation in Supabase
    2. Saves user message
    3. Routes through LangGraph agent (FAQ ’ RAG ’ Escalation)
    4. Saves AI response
    5. Returns response to user

    Args:
        request: MessageRequest with tenant_id, user_id, channel, content

    Returns:
        MessageResponse with AI response, intent, confidence, sources
    """
    try:
        logger.info(f"=é Incoming message from {request.user_id} via {request.channel}")

        # Get or create conversation
        conversation = await supabase_service.get_or_create_conversation(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            channel=request.channel
        )

        conversation_id = conversation["id"]

        # Save user message
        await supabase_service.save_message(
            conversation_id=conversation_id,
            role="user",
            content=request.content
        )

        # Create agent
        agent = create_agent(
            tenant_id=request.tenant_id,
            conversation_id=conversation_id,
            user_id=request.user_id,
            channel=request.channel,
            use_checkpointer=True  # Enable state persistence
        )

        # Process message through agent
        result = await agent.process_message(request.content)

        # Save AI response
        await supabase_service.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result["response"],
            metadata={
                "intent": result["intent"],
                "confidence": result["confidence"],
                "sources": result["sources"],
                "escalated": result["escalated"]
            }
        )

        # Return response
        return MessageResponse(
            response=result["response"],
            conversation_id=conversation_id,
            intent=result["intent"],
            sources=result["sources"],
            confidence=result["confidence"],
            escalated=result["escalated"]
        )

    except Exception as e:
        logger.error(f"L Error handling message: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation history.

    Args:
        conversation_id: Conversation ID

    Returns:
        List of messages in the conversation
    """
    try:
        messages = await supabase_service.get_conversation_history(
            conversation_id=conversation_id,
            limit=100
        )

        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "total": len(messages)
        }

    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation: {str(e)}"
        )


@app.get("/api/v1/tenants/{tenant_id}/conversations")
async def list_tenant_conversations(tenant_id: str, limit: int = 50):
    """
    List all conversations for a tenant.

    Args:
        tenant_id: Tenant ID
        limit: Maximum number of conversations to return

    Returns:
        List of conversations
    """
    try:
        result = supabase_service.client.table("conversations").select("*").eq(
            "tenant_id", tenant_id
        ).order("last_message_at", desc=True).limit(limit).execute()

        return {
            "tenant_id": tenant_id,
            "conversations": result.data,
            "total": len(result.data)
        }

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing conversations: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
