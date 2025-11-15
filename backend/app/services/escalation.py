"""
Escalation Service
Handles escalation of customer conversations to human support via email
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import resend

from app.db.session import get_db

logger = logging.getLogger(__name__)


class Escalation:
    """Service for escalating conversations to human support"""

    def __init__(self, user_id: str, conversation_id: str):
        self.user_id = user_id
        self.conversation_id = conversation_id

        # Configure Resend API key
        resend_api_key = os.getenv("RESEND_API_KEY")
        if resend_api_key:
            resend.api_key = resend_api_key
        else:
            logger.warning("RESEND_API_KEY not found in environment variables")

    async def create_escalation(
        self,
        message: str,
        confidence: float,
        reason: str
    ) -> Optional[str]:
        """
        Create escalation record and send email notification

        Args:
            message: Summary of the escalation
            confidence: Confidence level (0-1)
            reason: Reason for escalation

        Returns:
            escalation_id if successful, None otherwise
        """
        try:
            logger.info(f"[ESCALATION] Creating escalation for conversation {self.conversation_id}")

            # 1. Get escalation email from environment (no tenant logic)
            escalation_email = os.getenv("DEFAULT_ESCALATION_EMAIL", "support@example.com")
            logger.info(f"[ESCALATION] Using escalation email: {escalation_email}")

            # 2. Get conversation history for context
            messages = await self._get_conversation_history()

            # 3. Create escalation record (no tenant_id required)
            escalation_data = {
                "conversation_id": str(self.conversation_id),
                "reason": reason,
                "summary": message,
                "status": "pending",
                "assigned_to": escalation_email,
                "created_at": datetime.utcnow().isoformat()
            }

            db = get_db()
            escalation = db.table("escalations").insert(escalation_data).execute()

            if not escalation.data:
                logger.error("Failed to create escalation record")
                return None

            escalation_id = escalation.data[0]["id"]
            logger.info(f"[ESCALATION] Record created: {escalation_id}")

            # 4. Send email notification
            email_sent = await self._send_escalation_email(
                to_email=escalation_email,
                reason=reason,
                summary=message,
                conversation_history=messages,
                escalation_id=escalation_id,
                confidence=confidence
            )

            if not email_sent:
                logger.warning(f"Email notification failed for escalation {escalation_id}")

            # 5. Update conversation status
            try:
                db = get_db()
                db.table("conversations").update({
                    "status": "escalated",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", str(self.conversation_id)).execute()
                logger.info(f"[ESCALATION] Conversation status updated to 'escalated'")
            except Exception as e:
                logger.error(f"Failed to update conversation status: {e}")

            logger.info(f"✅ Escalation created successfully: {escalation_id}")
            return str(escalation_id)

        except Exception as e:
            logger.error(f"❌ Escalation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _send_escalation_email(
        self,
        to_email: str,
        reason: str,
        summary: str,
        conversation_history: List[Dict[str, Any]],
        escalation_id: str,
        confidence: float
    ) -> bool:
        """Send escalation email via Resend"""

        try:
            # Get app name from environment or use default
            app_name = os.getenv("APP_NAME", "AI Support")
            # Format conversation history
            history_html = "<ul style='list-style-type: none; padding-left: 0;'>"
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                created = msg.get("created_at", "")

                # Color code by role
                color = "#2196F3" if role == "USER" else "#4CAF50"
                history_html += f"""
                <li style='margin-bottom: 10px; padding: 10px; background-color: #f5f5f5; border-left: 3px solid {color};'>
                    <strong style='color: {color};'>{role}</strong>
                    <span style='color: #666; font-size: 12px;'>({created})</span>
                    <p style='margin: 5px 0 0 0;'>{content}</p>
                </li>
                """
            history_html += "</ul>"

            # Confidence indicator
            confidence_pct = int(confidence * 100)
            confidence_color = "#f44336" if confidence < 0.5 else "#ff9800" if confidence < 0.8 else "#4CAF50"

            # Build email HTML
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 700px;
                        margin: 20px auto;
                        background-color: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background-color: #f44336;
                        color: white;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                    }}
                    .content {{
                        padding: 30px 20px;
                    }}
                    .info-box {{
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #4CAF50;
                        color: white !important;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .footer {{
                        background-color: #f5f5f5;
                        padding: 20px;
                        font-size: 12px;
                        color: #666;
                        text-align: center;
                    }}
                    .detail-row {{
                        margin: 10px 0;
                        padding: 10px;
                        background-color: #f9f9f9;
                        border-radius: 4px;
                    }}
                    .detail-row strong {{
                        color: #333;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚨 Escalation Alert</h1>
                        <p style="margin: 10px 0 0 0; font-size: 18px;">{app_name}</p>
                    </div>
                    <div class="content">
                        <h2 style="color: #f44336; margin-top: 0;">Escalation Details</h2>

                        <div class="detail-row">
                            <strong>Reason:</strong> {reason}
                        </div>

                        <div class="detail-row">
                            <strong>Summary:</strong> {summary}
                        </div>

                        <div class="detail-row">
                            <strong>Confidence Level:</strong>
                            <span style="color: {confidence_color}; font-weight: bold;">{confidence_pct}%</span>
                        </div>

                        <div class="detail-row">
                            <strong>Escalation ID:</strong>
                            <code style="background-color: #e0e0e0; padding: 2px 6px; border-radius: 3px;">{escalation_id}</code>
                        </div>

                        <div class="info-box">
                            <strong>⚠️ Action Required</strong>
                            <p style="margin: 5px 0 0 0;">Please review this escalation and respond to the customer as soon as possible.</p>
                        </div>

                        <h3>Recent Conversation History</h3>
                        {history_html}

                        <div style="text-align: center;">
                            <a href="{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/conversations/{self.conversation_id}"
                               class="button">
                                View Full Conversation →
                            </a>
                        </div>
                    </div>
                    <div class="footer">
                        <p>Generated by CustomerAI Agent</p>
                        <p>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send via Resend
            resend_domain = os.getenv("RESEND_DOMAIN", "resend.dev")
            from_email = f"{app_name} <escalations@{resend_domain}>"

            params = {
                "from": from_email,
                "to": [to_email],
                "subject": f"🚨 Escalation: {reason} - {app_name}",
                "html": html_body,
                "tags": [
                    {"name": "type", "value": "escalation"},
                    {"name": "conversation", "value": str(self.conversation_id)[:8]}
                ]
            }

            email_result = resend.Emails.send(params)
            logger.info(f"📧 Escalation email sent: {email_result}")

            return True

        except Exception as e:
            logger.error(f"Failed to send escalation email: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        try:
            db = get_db()
            result = db.table("conversation_messages").select("*").eq(
                "conversation_id", str(self.conversation_id)
            ).order("created_at", desc=False).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return []
