"""
Booking Service
Handles appointment scheduling via Cal.com API
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.session import get_db

logger = logging.getLogger(__name__)

# Cal.com API Configuration
CAL_API_BASE = os.getenv("CAL_API_BASE", "https://api.cal.com/v2")
CAL_API_VERSION = os.getenv("CAL_API_VERSION", "2024-08-13")


class AvailableSlot(BaseModel):
    """Available time slot"""
    start: str
    end: str


class BookingRequest(BaseModel):
    """Booking request parameters"""
    attendee_name: str
    attendee_email: str
    attendee_phone: Optional[str] = None
    timezone: str = "Europe/Paris"
    start_time: str  # ISO 8601 format in UTC
    duration_minutes: int = 30
    notes: Optional[str] = None


class BookingResult(BaseModel):
    """Booking result"""
    success: bool
    booking_id: Optional[str] = None
    meeting_url: Optional[str] = None
    scheduled_at: Optional[str] = None
    error_message: Optional[str] = None


class BookingService:
    """Service for scheduling appointments via Cal.com"""

    def __init__(self, user_id: str, conversation_id: str):
        self.user_id = user_id
        self.conversation_id = conversation_id

    async def check_availability(
        self,
        start_date: str,
        end_date: str,
        timezone: str = "Europe/Paris"
    ) -> List[AvailableSlot]:
        """
        Check available time slots for booking

        Args:
            start_date: Start date in ISO 8601 format (e.g., "2025-11-20T00:00:00Z")
            end_date: End date in ISO 8601 format (e.g., "2025-11-21T00:00:00Z")
            timezone: Timezone for the slots (default: Europe/Paris)

        Returns:
            List of available time slots
        """
        try:
            logger.info(f"[AVAILABILITY] Checking slots from {start_date} to {end_date}")

            # Get Cal.com config from environment (no tenant logic)
            cal_api_key = os.getenv("CAL_API_KEY")
            cal_event_type_id = os.getenv("CAL_EVENT_TYPE_ID")

            if not cal_api_key or not cal_event_type_id:
                logger.error("Missing Cal.com config in environment variables")
                return []

            # Call Cal.com API to get available slots
            slots = await self._fetch_available_slots(
                api_key=cal_api_key,
                event_type_id=int(cal_event_type_id),
                start_date=start_date,
                end_date=end_date,
                timezone=timezone
            )

            logger.info(f"✅ Found {len(slots)} available slots")
            return slots

        except Exception as e:
            logger.error(f"❌ Availability check failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def create_booking(
        self,
        attendee_name: str,
        attendee_email: str,
        start_time: str,
        duration_minutes: int = 30,
        attendee_phone: Optional[str] = None,
        timezone: str = "Europe/Paris"
    ) -> BookingResult:
        """
        Create a booking via Cal.com API

        Args:
            attendee_name: Customer's full name
            attendee_email: Customer's email
            start_time: Booking start time in ISO 8601 UTC format
            duration_minutes: Meeting duration (default: 30)
            attendee_phone: Optional phone number in international format
            timezone: Customer's timezone (default: Europe/Paris)

        Returns:
            BookingResult with success status and details
        """
        try:
            logger.info(f"[BOOKING] Creating booking for {attendee_name} at {start_time}")

            # 1. Get Cal.com config from environment (no tenant logic)
            cal_api_key = os.getenv("CAL_API_KEY")
            cal_event_type_id = os.getenv("CAL_EVENT_TYPE_ID")

            if not cal_api_key or not cal_event_type_id:
                logger.error("Missing Cal.com config in environment variables")
                return BookingResult(
                    success=False,
                    error_message="Booking system not configured"
                )

            # 2. Create booking via Cal.com API
            booking_data = await self._call_cal_api(
                api_key=cal_api_key,
                event_type_id=int(cal_event_type_id),
                attendee_name=attendee_name,
                attendee_email=attendee_email,
                start_time=start_time,
                duration_minutes=duration_minutes,
                attendee_phone=attendee_phone,
                timezone=timezone
            )

            if not booking_data:
                return BookingResult(
                    success=False,
                    error_message="Failed to create booking with Cal.com"
                )

            # 3. Store booking in database (no tenant_id)
            db = get_db()
            meeting_record = db.table("meetings").insert({
                "conversation_id": str(self.conversation_id),
                "user_id": self.user_id,
                "meeting_url": booking_data.get("location") or booking_data.get("meetingUrl"),
                "scheduled_at": start_time,
                "duration_minutes": duration_minutes,
                "status": "scheduled",
                "cal_event_id": booking_data.get("uid"),
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            booking_id = meeting_record.data[0]["id"]
            logger.info(f"✅ Booking created: {booking_id}")

            return BookingResult(
                success=True,
                booking_id=str(booking_id),
                meeting_url=booking_data.get("location") or booking_data.get("meetingUrl"),
                scheduled_at=start_time,
                error_message=None
            )

        except Exception as e:
            logger.error(f"❌ Booking creation failed: {e}")
            import traceback
            traceback.print_exc()
            return BookingResult(
                success=False,
                error_message=str(e)
            )

    async def _fetch_available_slots(
        self,
        api_key: str,
        event_type_id: int,
        start_date: str,
        end_date: str,
        timezone: str
    ) -> List[AvailableSlot]:
        """Fetch available slots from Cal.com API"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "cal-api-version": CAL_API_VERSION
        }

        params = {
            "eventTypeId": event_type_id,
            "startTime": start_date,
            "endTime": end_date,
            "timeZone": timezone
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CAL_API_BASE}/slots/available",
                    headers=headers,
                    params=params,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    slots_data = result.get("data", {}).get("slots", [])

                    # Convert to AvailableSlot objects
                    slots = []
                    for slot in slots_data:
                        slots.append(AvailableSlot(
                            start=slot.get("time"),
                            end=slot.get("time")  # Cal.com returns start time, end is calculated
                        ))

                    return slots
                else:
                    logger.error(f"Cal.com API error (availability): {response.status_code} - {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching available slots: {e}")
            return []

    async def _call_cal_api(
        self,
        api_key: str,
        event_type_id: int,
        attendee_name: str,
        attendee_email: str,
        start_time: str,
        duration_minutes: int,
        attendee_phone: Optional[str],
        timezone: str
    ) -> Optional[Dict[str, Any]]:
        """Call Cal.com API to create booking"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "cal-api-version": CAL_API_VERSION
        }

        payload = {
            "start": start_time,
            "eventTypeId": event_type_id,
            "attendee": {
                "name": attendee_name,
                "email": attendee_email,
                "timeZone": timezone
            }
        }

        # Add optional phone number
        if attendee_phone:
            payload["attendee"]["phoneNumber"] = attendee_phone

        # Add duration override if different from event type default
        if duration_minutes != 30:
            payload["lengthInMinutes"] = duration_minutes

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CAL_API_BASE}/bookings",
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 201:
                    result = response.json()
                    return result.get("data")
                else:
                    logger.error(f"Cal.com API error (booking): {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error calling Cal.com API: {e}")
            return None
