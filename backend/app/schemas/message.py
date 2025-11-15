from pydantic import BaseModel
from typing import List, Optional


class MessageRequest(BaseModel):
    user_id: str
    channel: str
    content: str


class MessageResponse(BaseModel):
    response: str
    conversation_id: str
    intent: Optional[str] = None
    sources: Optional[List[str]] = None
    confidence: Optional[float] = None
    escalated: Optional[bool] = False
