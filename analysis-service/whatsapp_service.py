"""
Wasender WhatsApp Integration for Akruti Aesthetics Clinic (Workflow 6).
Sends automated WhatsApp messages containing clinic details, addresses,
contact numbers, and caller-requested procedure/booking information.
"""

import logging
import os
import re
import httpx

logger = logging.getLogger(__name__)

WASENDER_URL = os.getenv("WASENDER_URL", "https://wasenderapi.com/api/send-message")
WASENDER_TOKEN = os.getenv(
    "WASENDER_TOKEN",
    "2de4a0aa5cd1ca6f8a890b7d78792abbd403b8d58313f33b5df882df00e4dbf8"
)

def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to standard E.164 string format (+91XXXXXXXXXX)."""
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return cleaned
    if len(cleaned) == 10 and cleaned.startswith(("6", "7", "8", "9")):
        return f"+91{cleaned}"
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return f"+{cleaned}"
    return f"+{cleaned}"

async def send_whatsapp_clinic_details(
    phone_number: str,
    caller_name: str = None,
    procedure_of_interest: str = None,
    booking_requested: bool = False,
    preferred_date_time: str = None
) -> bool:
    """
    Sends WhatsApp message with clinic name, address, numbers, and requested procedure/booking details
    via Wasender API.
    """
    target_phone = normalize_phone_number(phone_number)
    if not target_phone:
        logger.error(f"Invalid phone number provided for WhatsApp dispatch: '{phone_number}'")
        return False

    name_str = f"Dear {caller_name.strip()},\n\n" if caller_name and caller_name.strip() else ""

    extra_details = []
    if procedure_of_interest and procedure_of_interest.strip():
        extra_details.append(f"✨ *Procedure of Interest*: {procedure_of_interest.strip()}")
    if booking_requested:
        time_str = f" ({preferred_date_time.strip()})" if preferred_date_time and preferred_date_time.strip() else ""
        extra_details.append(f"📅 *Consultation Booking Request*: Registered{time_str}")

    extra_section = ("\n" + "\n".join(extra_details) + "\n") if extra_details else "\n"

    message_text = (
        "🏥 *Akruti Aesthetics & Plastic Surgery Clinic*\n"
        "*(Lead Surgeon: Dr. Kaushal Priya Anand, M.B.B.S, M.S, M.Ch Plastic Surgeon)*\n\n"
        f"{name_str}"
        "Thank you for reaching out to us! Here are the clinic location & contact details:\n\n"
        "📍 *Durgapur Clinic*:\n"
        "1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216\n\n"
        "📍 *Burdwan Clinic*:\n"
        "S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan\n\n"
        "📞 *Contact Phone Numbers*:\n"
        "+91 90020 08137 / +91 90020 08147 / +91 8031336640\n\n"
        "✉️ *Email*: akrutiaestheticsurgery@gmail.com\n"
        "🕒 *Clinic Hours*: Monday – Friday, 9:00 AM – 7:00 PM\n"
        f"{extra_section}\n"
        "Our team will be delighted to assist you further. Feel free to call us directly for appointments!"
    )

    headers = {
        "Authorization": f"Bearer {WASENDER_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": target_phone,
        "text": message_text
    }

    logger.info(f"Dispatching WhatsApp message to {target_phone} via Wasender API...")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(WASENDER_URL, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"WhatsApp message successfully sent to {target_phone}: {resp.text}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message ({resp.status_code}): {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Error calling Wasender API for {target_phone}: {e}")
        return False
