"""Social Account schemas"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class AuthURL(BaseModel):
    """Authorization URL response"""
    authorization_url: str


class SocialAccount(BaseModel):
    """Social media account"""
    id: str
    platform: str
    account_id: str
    username: Optional[str] = None
    account_name: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
