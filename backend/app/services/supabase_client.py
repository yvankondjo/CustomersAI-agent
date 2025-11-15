from app.db.session import get_db
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_db()
        return self._client

    async def get_or_create_conversation(
        self, user_id: str, channel: str
    ) -> Dict[str, Any]:
        result = (
            self.client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("channel", channel)
            .execute()
        )

        if result.data:
            return result.data[0]

        new_conv = (
            self.client.table("conversations")
            .insert(
                {
                    "user_id": user_id,
                    "channel": channel,
                    "status": "open",
                }
            )
            .execute()
        )

        return new_conv.data[0]

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = (
            self.client.table("conversation_messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )

        return result.data[0]

    async def get_conversation_history(
        self, conversation_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        result = (
            self.client.table("conversation_messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )

        return result.data


supabase_service = SupabaseService()

