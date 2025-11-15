import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.schemas.messages import (
    UnifiedMessageContent,
    MessageSaveRequest,
    MessageSaveResponse,
    Platform,
    UnifiedMessageType,
)
from app.services.instagram_service import InstagramService
from app.db.session import get_db
from app.services.rag_agent import create_rag_agent
from app.deps.runtime_prod import CHECKPOINTER_POSTGRES
from app.core.constants import DEFAULT_USER_ID

logger = logging.getLogger(__name__)


async def get_user_credentials_by_platform_account(
    platform: str, account_id: str
) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        result = (
            db.table("social_accounts")
            .select("*")
            .eq("platform", platform)
            .eq("account_id", account_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des credentials: {e}")
        return None


async def process_incoming_message_for_user(
    message: Dict[str, Any], user_info: Dict[str, Any]
) -> None:
    await handle_instagram_messages_webhook(
        value={"messages": [message]}, user_info=user_info
    )


async def handle_instagram_messages_webhook(
    value: Dict[str, Any],
    user_info: Dict[str, Any],
) -> None:
    messages = value.get("messages", [])
    if not messages:
        logger.info("Aucun message reçu dans le webhook Instagram")
        return

    for message in messages:
        await process_incoming_instagram_message(message, user_info)


async def process_incoming_instagram_message(
    message: Dict[str, Any],
    user_info: Dict[str, Any],
) -> Optional[str]:
    platform_enum = Platform.INSTAGRAM
    extracted_message = await extract_instagram_message_content(message)
    if extracted_message is None:
        logger.warning("Impossible d'extraire le contenu du message Instagram: %s", message)
        return None

    save_response = None
    conversation_id = None
    customer_instagram_id = None

    try:
        save_request = MessageSaveRequest(
            platform=platform_enum,
            extracted_message=extracted_message,
            user_info=user_info,
            customer_name=extracted_message.customer_name,
            customer_identifier=extracted_message.message_from,
        )

        save_response = await save_unified_message(save_request)
        if not save_response.success or not save_response.conversation_message_id:
            logger.error("Message Instagram (inbound) non sauvegardé en base")
            return None

        conversation_id = save_response.conversation_id
        customer_instagram_id = extracted_message.message_from

        logger.info(
            "Message Instagram INBOUND sauvegardé (conversation_id=%s, message_id=%s)",
            save_response.conversation_id,
            save_response.conversation_message_id,
        )

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du message INBOUND Instagram: {e}")
        return None

    if not conversation_id:
        logger.error("conversation_id manquant après sauvegarde")
        return None

    reply_text = None
    user_id = str(user_info.get("user_id") or DEFAULT_USER_ID)

    try:
        agent = create_rag_agent(
            user_id=user_id,
            conversation_id=conversation_id,
            checkpointer=CHECKPOINTER_POSTGRES
        )

        result = await agent.process_message(extracted_message.content)

        reply_text = result.get("response", "Désolé, je n'ai pas pu traiter votre message.")

        sent = await send_instagram_text_message(
            user_info=user_info,
            to_instagram_id=customer_instagram_id,
            content=reply_text,
        )

        if not sent:
            logger.error(
                "Échec d'envoi de la réponse automatique Instagram à %s",
                customer_instagram_id,
            )
            return save_response.conversation_message_id if save_response else None

    except Exception as e:
        logger.error(f"Erreur lors de la génération/envoi de la réponse: {e}")
        return save_response.conversation_message_id if save_response else None

    if not reply_text:
        logger.error("Aucune réponse générée par l'agent RAG")
        return save_response.conversation_message_id if save_response else None

    try:
        outbound_message_id = save_outbound_message_to_db(
            conversation_id=conversation_id,
            content=reply_text,
            user_id=user_id,
            platform=platform_enum,
        )
        logger.info(
            "Message Instagram OUTBOUND sauvegardé (conversation_id=%s, message_id=%s)",
            conversation_id,
            outbound_message_id,
        )
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du message OUTBOUND: {e}")

    return save_response.conversation_message_id if save_response else None


async def extract_instagram_message_content(
    message: Dict[str, Any],
) -> Optional[UnifiedMessageContent]:
    if not message:
        return None

    raw_text = (message.get("text") or "").strip()
    if not raw_text:
        logger.warning("Message Instagram sans texte: %s", message)
        return None

    token_count = len(raw_text.split())

    raw_sender = message.get("from")
    if isinstance(raw_sender, dict):
        raw_sender = raw_sender.get("id") or raw_sender.get("user_id") or raw_sender.get("username")
    if not raw_sender:
        logger.warning("Message Instagram sans identifiant expéditeur: %s", message)
        return None
    sender_id = str(raw_sender)

    contact_info = message.get("_contact_info", {})
    customer_name = contact_info.get("name") if contact_info else None

    return UnifiedMessageContent(
        content=raw_text,
        token_count=token_count,
        message_type=UnifiedMessageType.TEXT,
        message_id=message.get("mid") or message.get("id"),
        message_from=sender_id,
        platform=Platform.INSTAGRAM,
        customer_name=customer_name,
    )


async def save_unified_message(request: MessageSaveRequest) -> MessageSaveResponse:
    try:
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = await get_or_create_conversation(
                platform=request.platform,
                user_info=request.user_info,
                customer_identifier=request.extracted_message.message_from,
                customer_name=request.customer_name,
            )

        if not conversation_id:
            return MessageSaveResponse(
                success=False,
                error=(
                    f"Impossible de créer/récupérer la conversation pour "
                    f"{request.extracted_message.message_from}"
                ),
            )

        message_data = prepare_message_data_for_db(
            extracted_message=request.extracted_message,
            conversation_id=conversation_id,
            customer_identifier=(
                request.customer_identifier or request.extracted_message.message_from
            ),
            direction="inbound",
        )

        res = save_message_to_db(message_data)
        if res and res.data:
            conversation_message_id = str(res.data[0]["id"])

            update_conversation_state(
                conversation_id=conversation_id,
                role="user",
                content=request.extracted_message.content,
                metadata_updates={
                    "customer_identifier": request.extracted_message.message_from,
                    "customer_name": request.customer_name
                    or request.extracted_message.customer_name
                    or request.extracted_message.message_from,
                },
                status="open",
            )

            return MessageSaveResponse(
                success=True,
                conversation_message_id=conversation_message_id,
                conversation_id=conversation_id,
            )

        return MessageSaveResponse(success=False, error="Erreur lors de l'insertion en base")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du message unifié: {e}")
        return MessageSaveResponse(success=False, error=str(e))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_conversation_state(
    conversation_id: str,
    role: str,
    content: str,
    metadata_updates: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> None:
    db = get_db()
    try:
        current = (
            db.table("conversations")
            .select("metadata")
            .eq("id", conversation_id)
            .single()
            .execute()
        )
        metadata = current.data.get("metadata") if current and current.data else {}
    except Exception as error:
        logger.warning("Impossible de récupérer la conversation %s: %s", conversation_id, error)
        metadata = {}

    if not isinstance(metadata, dict):
        metadata = {}

    if metadata_updates:
        for key, value in metadata_updates.items():
            if value is None:
                continue
            metadata[key] = value

    metadata["last_message_preview"] = content[:280] if content else ""
    metadata["last_message_role"] = role

    timestamp = _now_iso()

    payload: Dict[str, Any] = {
        "metadata": metadata,
        "last_message_at": timestamp,
        "updated_at": timestamp,
    }

    if status:
        payload["status"] = status

    try:
        db.table("conversations").update(payload).eq("id", conversation_id).execute()
    except Exception as error:
        logger.warning("Impossible de mettre à jour la conversation %s: %s", conversation_id, error)


async def get_or_create_conversation(
    platform: Platform,
    user_info: Dict[str, Any],
    customer_identifier: str,
    customer_name: Optional[str] = None,
) -> Optional[str]:
    try:
        db = get_db()

        owner_user_id = str(user_info.get("user_id") or DEFAULT_USER_ID)
        channel = platform.value

        res_find = (
            db.table("conversations")
            .select("id")
            .eq("user_id", owner_user_id)
            .eq("channel", channel)
            .contains("metadata", {"customer_identifier": customer_identifier})
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        rows = res_find.data or []
        if rows:
            return str(rows[0]["id"])

        metadata = {
            "customer_identifier": customer_identifier,
            "customer_name": customer_name or customer_identifier,
            "social_account_id": str(user_info.get("social_account_id") or ""),
            "account_id": str(user_info.get("account_id") or ""),
            "account_username": user_info.get("account_username"),
        }

        metadata = {key: value for key, value in metadata.items() if value}

        res_create = (
            db.table("conversations")
            .insert(
                {
                    "user_id": owner_user_id,
                    "channel": channel,
                    "status": "open",
                    "last_message_at": _now_iso(),
                    "metadata": metadata,
                }
            )
            .execute()
        )
        if res_create and res_create.data:
            first = res_create.data[0]
            return str(first.get("id")) if first and first.get("id") else None

        return None
    except Exception as e:
        logger.error(f"Erreur lors de la gestion de la conversation: {e}")
        return None


def prepare_message_data_for_db(
    extracted_message: UnifiedMessageContent,
    conversation_id: str,
    customer_identifier: Optional[str],
    direction: str,
) -> Dict[str, Any]:
    role = "user" if direction == "inbound" else "assistant"

    metadata: Dict[str, Any] = {
        "platform": extracted_message.platform.value,
        "direction": direction,
        "external_message_id": extracted_message.message_id,
        "sender_id": customer_identifier or extracted_message.message_from,
        "message_type": extracted_message.message_type.value,
        "token_count": extracted_message.token_count,
        "customer_identifier": customer_identifier or extracted_message.message_from,
    }

    return {
        "conversation_id": conversation_id,
        "role": role,
        "content": extracted_message.content,
        "metadata": metadata,
    }


def save_message_to_db(message_data: Dict[str, Any]) -> Any:
    db = get_db()
    return db.table("conversation_messages").insert(message_data).execute()


async def send_instagram_text_message(
    user_info: Dict[str, Any],
    to_instagram_id: str,
    content: str,
) -> bool:
    access_token = user_info.get("access_token")
    account_id = user_info.get("account_id")

    if not access_token or not account_id:
        logger.error("Credentials Instagram manquants dans user_info")
        return False

    service = InstagramService(access_token, account_id)
    result = await service.send_direct_message(to_instagram_id, content)

    success = bool(result.get("success"))
    if not success:
        logger.error("Échec send_direct_message Instagram: %s", result)

    return success


async def send_message_from_user_to_customer(
    conversation_id: str,
    user_info: Dict[str, Any],
    customer_instagram_id: str,
    content: str,
) -> Optional[str]:
    sent = await send_instagram_text_message(
        user_info=user_info,
        to_instagram_id=customer_instagram_id,
        content=content,
    )

    if not sent:
        logger.error(
            "Échec d'envoi du message utilisateur vers le client Instagram %s",
            customer_instagram_id,
        )
        return None

    try:
        message_id = save_outbound_message_to_db(
            conversation_id=conversation_id,
            content=content,
            user_id=str(user_info.get("user_id") or "user"),
            platform=Platform.INSTAGRAM,
        )
        logger.info(
            "Message OUTBOUND utilisateur sauvegardé (conversation_id=%s, message_id=%s)",
            conversation_id,
            message_id,
        )
        return message_id
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du message OUTBOUND utilisateur: {e}")
        return None


def save_outbound_message_to_db(
    conversation_id: str,
    content: str,
    user_id: str,
    platform: Platform,
) -> Optional[str]:
    try:
        db = get_db()
        metadata = {
            "platform": platform.value,
            "direction": "outbound",
            "sender_id": user_id,
            "message_type": "text",
        }

        res = (
            db.table("conversation_messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": content,
                    "metadata": metadata,
                }
            )
            .execute()
        )

        message_id = str(res.data[0]["id"]) if res and res.data else None

        if message_id:
            update_conversation_state(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata_updates={"last_sender_id": user_id},
            )

        return message_id
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du message OUTBOUND: {e}")
        return None

