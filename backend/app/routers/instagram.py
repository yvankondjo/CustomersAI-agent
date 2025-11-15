from fastapi import APIRouter, HTTPException, status, Request, Query
from fastapi.responses import PlainTextResponse
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from app.schemas.instagram import (
    DirectMessageRequest,
    InstagramCredentials,
    InstagramCredentialsValidation,
    InstagramMessageResponse,
    ConversationsResponse,
    InstagramAccountCreate,
)
from app.services.instagram_service import get_instagram_service, InstagramService
from app.services.response_manager import (
    process_incoming_message_for_user,
    get_user_credentials_by_platform_account,
)
from app.db.session import get_db
from fastapi import Depends
from supabase import Client

router = APIRouter(prefix="/api/instagram", tags=["Instagram"])
logger = logging.getLogger(__name__)


@router.post("/validate-credentials", response_model=InstagramCredentialsValidation)
async def validate_instagram_credentials(credentials: InstagramCredentials):
    """Valider les credentials Instagram Business API"""
    try:
        async with InstagramService(
            credentials.access_token, credentials.page_id
        ) as service:
            validation_result = await service.validate_credentials()
            return InstagramCredentialsValidation(**validation_result)
    except Exception as e:
        logger.error(f"Error validation Instagram: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validation: {str(e)}",
        )


@router.post("/send-dm", response_model=InstagramMessageResponse)
async def send_direct_message(request: DirectMessageRequest):
    """Send a direct message Instagram"""
    try:
        service = await get_instagram_service(request.access_token, request.page_id)
        result = await service.send_direct_message(
            request.recipient_ig_id, request.text
        )

        return InstagramMessageResponse(
            success=True, message_id=result.get("message_id")
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error send DM Instagram: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error send DM: {str(e)}",
        )


@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(
    access_token: str = None, page_id: str = None, limit: int = 25
):
    """Get the conversations of direct messages"""
    try:
        service = await get_instagram_service(access_token, page_id)
        result = await service.get_conversations(limit)
        return ConversationsResponse(**result)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error get conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error conversations: {str(e)}",
        )


@router.get("/health")
async def instagram_health_check():
    """Check the health of the Instagram service"""
    try:
        service = await get_instagram_service()
        validation = await service.validate_credentials()

        return {
            "service": "instagram",
            "status": "healthy" if validation["valid"] else "unhealthy",
            "details": validation,
        }
    except Exception as e:
        logger.error(f"Error health check Instagram: {e}")
        return {"service": "instagram", "status": "unhealthy", "error": str(e)}


@router.get("/account")
async def get_instagram_account(
    account_id: str = Query(None, description="Instagram Business Account ID"),
    username: str = Query(None, description="Instagram username"),
    db: Client = Depends(get_db)
):
    """Récupère un compte Instagram depuis la base de données"""
    try:
        query = db.table("social_accounts").select("*").eq("platform", "instagram")
        
        if account_id:
            query = query.eq("account_id", account_id)
        elif username:
            query = query.eq("account_username", username)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="account_id ou username requis"
            )
        
        result = query.execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Compte Instagram non trouvé"
            )
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du compte Instagram: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.post("/account")
async def create_or_update_instagram_account(
    account_data: InstagramAccountCreate,
    db: Client = Depends(get_db)
):
    """Crée ou met à jour un compte Instagram dans la base de données"""
    try:
        social_account_data = {
            "platform": "instagram",
            "account_id": account_data.account_id,
            "account_username": account_data.account_username,
            "access_token": account_data.access_token,
            "token_expires_at": account_data.token_expires_at,
            "is_active": account_data.is_active,
        }
        
        result = db.table("social_accounts").upsert(
            social_account_data,
            on_conflict="platform,account_id"
        ).execute()
        
        if result.data:
            return result.data[0]
        return social_account_data
    except Exception as e:
        logger.error(f"Erreur lors de la création/mise à jour du compte Instagram: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


# ==================== WEBHOOKS INSTAGRAM ====================


@router.get("/webhook")
async def instagram_webhook_verification(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """
    Verification of the Instagram webhook (activation step)

    Meta sends a GET request to verify that your endpoint is valid
    """
    verify_token = os.getenv("INSTAGRAM_VERIFY_TOKEN")

    if not verify_token:
        logger.error("INSTAGRAM_VERIFY_TOKEN not configured")
        raise HTTPException(status_code=500, detail="Verification token not configured")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("Webhook Instagram verified successfully")
        return PlainTextResponse(content=hub_challenge)

    logger.warning(
        f"Webhook Instagram verification failed: mode={hub_mode}, token_match={hub_verify_token == verify_token}"
    )
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/webhook")
async def instagram_webhook_handler(request: Request):
    """
    Main handler for Instagram webhooks

    Receives:
    - Incoming direct messages (inbox)
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Webhook Instagram received: {webhook_data}")

        for entry in webhook_data.get("entry", []):
            logger.info(f"Processing Instagram webhook for entry: {entry}")
            await process_instagram_webhook_entry_with_user_routing(entry)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Instagram webhook: {e}")
        return {"status": "error", "message": str(e)}


async def process_instagram_webhook_entry_with_user_routing(entry: dict):
    """Process an entry of Instagram webhook with user routing"""
    instagram_business_account_id = entry.get("id")
    messaging = entry.get("messaging", [])

    if not instagram_business_account_id:
        logger.warning("Instagram webhook entry missing account ID")
        return

    credentials = await get_user_credentials_by_platform_account(
        platform="instagram", account_id=instagram_business_account_id
    )

    if not credentials:
        logger.warning(
            f"No account found for Instagram Business Account: {instagram_business_account_id}"
        )
        return

    if not credentials.get("is_active", False):
        logger.warning(
            f"Ignoring webhook for inactive Instagram account: {instagram_business_account_id}"
        )
        return

    if not credentials.get("access_token"):
        logger.error(
            f"Instagram account {instagram_business_account_id} has no access token"
        )
        return

    user_info = {
        "social_account_id": str(credentials.get("id")),
        "instagram_business_account_id": credentials.get("account_id"),
        "account_id": credentials.get("account_id"),
        "platform": "instagram",
        "access_token": credentials.get("access_token"),
        "account_username": credentials.get("account_username"),
    }

    logger.info(
        f"Webhook Instagram routed to account {instagram_business_account_id} (username: {user_info.get('account_username')})"
    )

    for message_event in messaging:
        await process_instagram_message_event(message_event, user_info)


async def process_instagram_message_event(message_event: dict, user_info: dict):
    """Process an Instagram direct message event"""
    try:
        if "message" in message_event:
            message = message_event["message"]

            # ⚠️ CRITICAL: Ignore echo messages (sent BY the user/page, not TO the user)
            # is_echo: True means the message was sent by the page itself
            if message.get("is_echo", False):
                logger.info(f"Ignoring echo message (sent by page): {message.get('text', '')[:50]}")
                return

            # Extract sender information from the webhook
            sender = message_event.get("sender", {})
            sender_id = sender.get("id")

            # Build contact info from sender data
            contact_info = None
            if sender_id:
                sender_username = sender.get("username") or sender.get("name")
                if sender_username:
                    contact_info = {"name": sender_username, "id": sender_id}

            raw_from = message.get("from")
            message_sender = sender_id
            if not message_sender:
                if isinstance(raw_from, dict):
                    message_sender = raw_from.get("id") or raw_from.get("user_id") or raw_from.get("username")
                else:
                    message_sender = raw_from
            if not message_sender:
                logger.warning("Impossible d'identifier l'expéditeur pour le message %s", message.get("mid"))
                return
            message_sender = str(message_sender)

            message_payload = dict(message)
            message_payload.pop("from", None)

            formatted_message = {
                **message_payload,
                "id": message.get("mid"),
                "from": message_sender,
                "timestamp": message_event.get("timestamp"),
            }

            # Add contact info if available
            if contact_info:
                formatted_message["_contact_info"] = contact_info

            await process_incoming_message_for_user(formatted_message, user_info)
    except Exception as e:
        logger.error(f"Error processing Instagram messaging event: {e}")
