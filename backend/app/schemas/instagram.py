from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class InstagramCredentials(BaseModel):
    access_token: str
    page_id: str


class InstagramCredentialsValidation(BaseModel):
    valid: bool
    account_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DirectMessageRequest(BaseModel):
    recipient_ig_id: str
    text: str
    access_token: Optional[str] = None
    page_id: Optional[str] = None


class FeedPostRequest(BaseModel):
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    caption: str
    access_token: Optional[str] = None
    page_id: Optional[str] = None


class StoryRequest(BaseModel):
    image_url: str
    access_token: Optional[str] = None
    page_id: Optional[str] = None


class InstagramMessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class ConversationsResponse(BaseModel):
    data: Optional[List[Dict[str, Any]]] = None
    paging: Optional[Dict[str, Any]] = None


class InstagramAccountCreate(BaseModel):
    account_id: str
    account_username: Optional[str] = None
    access_token: str
    token_expires_at: Optional[str] = None
    is_active: bool = True
