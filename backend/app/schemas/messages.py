from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    WEB = "web"
    WHATSAPP = "whatsapp"


class UnifiedMessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"


class UnifiedMessageContent(BaseModel):
    content: str
    token_count: int
    message_type: UnifiedMessageType
    message_id: Optional[str] = None
    message_from: Optional[str] = None
    platform: Platform
    customer_name: Optional[str] = None


class MessageSaveRequest(BaseModel):
    platform: Platform
    extracted_message: UnifiedMessageContent
    user_info: dict
    customer_name: Optional[str] = None
    customer_identifier: Optional[str] = None
    conversation_id: Optional[str] = None


class MessageSaveResponse(BaseModel):
    success: bool
    conversation_message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None

