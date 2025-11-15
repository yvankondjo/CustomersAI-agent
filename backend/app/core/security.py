"""Security utilities for authentication"""
import logging

logger = logging.getLogger(__name__)


def get_current_user_id() -> str:
    """
    Get current user ID from authentication

    For hackathon: Returns a demo user ID
    In production: Should decode JWT token and extract user_id
    """
    # Hackathon shortcut: return demo user ID
    return "demo-user-id"
