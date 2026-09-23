"""
Official Meta WhatsApp Cloud API Integration for Akruti Aesthetics Clinic (Workflow 1).
Supports:
1. 'clinic_details' - Static clinic overview & reception contacts.
2. 'appointment_confirmation' - Dynamic confirmed consultation with Header (Patient Name) + 3 Body variables (Date/Time, Branch, Address).
3. 'appointment_details' - Dynamic branch consultation hours & address (falls back to clinic_details if template not yet created).
"""

import logging
import os
import re
import httpx

logger = logging.getLogger(__name__)

WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", os.getenv("FB_WHATSAPP_ACCESS_TOKEN_2", ""))
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "1409910712203417")
WHATSAPP_TEMPLATE_LANG = os.getenv("WHATSAPP_TEMPLATE_LANG", "en")

# Clinic Branch Registry
CLINIC_BRANCHES = {
    "durgapur": {
        "name": "Durgapur Clinic",
        "address": "1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur 713216",
        "hours": "Mon–Fri: 9:00 AM – 7:00 PM"
    },
    "burdwan": {
        "name": "Burdwan Clinic",
        "address": "S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan",
        "hours": "Mon–Fri: 9:00 AM – 7:00 PM"
    }
}


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to digits-only E.164 string format for Meta Cloud API (e.g., 91XXXXXXXXXX).
    """
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d]", "", str(phone).strip())
    if not cleaned:
        return ""
    if len(cleaned) == 10 and cleaned.startswith(("6", "7", "8", "9")):
        return f"91{cleaned}"
    if len(cleaned) == 11 and cleaned.startswith("0"):
        return f"91{cleaned[1:]}"
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return cleaned
    return cleaned


async def send_whatsapp_template(
    phone_number: str,
    template_name: str,
    components: list = None,
    language_code: str = None
) -> dict:
    """
    Core dispatcher to Meta WhatsApp Cloud API.
    """
    target_phone = normalize_phone_number(phone_number)
    if not target_phone:
        logger.error(f"Invalid phone number provided for WhatsApp dispatch: '{phone_number}'")
        return {"success": False, "error": f"Invalid phone number: {phone_number}"}

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    lang = language_code or WHATSAPP_TEMPLATE_LANG

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": target_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": lang
            }
        }
    }
    if components:
        payload["template"]["components"] = components

    logger.info(f"Dispatching WhatsApp template '{template_name}' (lang={lang}) to {target_phone}...")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            status_code = resp.status_code

            try:
                res_json = resp.json()
            except Exception:
                res_json = {"raw": resp.text}

            if status_code in (200, 201):
                msg_id = res_json.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"WhatsApp template successfully sent to {target_phone} (id: {msg_id})")
                return {
                    "success": True,
                    "target_phone": target_phone,
                    "message_id": msg_id,
                    "template": template_name,
                    "language": lang,
                    "response": res_json
                }

            err_info = res_json.get("error", {})
            err_msg = err_info.get("message", resp.text)
            logger.warning(f"Meta Cloud API returned status {status_code} for template '{template_name}': {err_msg}")
            return {
                "success": False,
                "status_code": status_code,
                "error": f"Meta API Error: {err_msg}",
                "target_phone": target_phone,
                "template": template_name,
                "response": res_json
            }

    except Exception as e:
        logger.error(f"Error calling Meta WhatsApp Cloud API for {target_phone}: {e}")
        return {
            "success": False,
            "error": str(e),
            "target_phone": target_phone,
            "template": template_name
        }


async def send_whatsapp_clinic_details(
    phone_number: str,
    caller_name: str = None,
    procedure_of_interest: str = None
) -> dict:
    """
    Sends static 'clinic_details' template.
    """
    return await send_whatsapp_template(
        phone_number=phone_number,
        template_name="clinic_details"
    )


async def send_whatsapp_appointment_confirmation(
    phone_number: str,
    patient_name: str,
    appointment_datetime: str,
    branch_id_or_name: str
) -> dict:
    """
    Sends 'appointment_confirmation' template with:
    - Header (1 param): patient_name
    - Body (3 params): {{1}} Date & Time, {{2}} Branch Name, {{3}} Full Address
    """
    # Resolve branch details
    branch_key = (branch_id_or_name or "").lower()
    if "burdwan" in branch_key:
        branch_info = CLINIC_BRANCHES["burdwan"]
    else:
        branch_info = CLINIC_BRANCHES["durgapur"]

    formatted_name = (patient_name or "Valued Patient").strip()
    formatted_dt = (appointment_datetime or "Scheduled Consultation Time").strip()

    components = [
        {
            "type": "header",
            "parameters": [
                {"type": "text", "text": formatted_name}
            ]
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": formatted_dt},
                {"type": "text", "text": branch_info["name"]},
                {"type": "text", "text": branch_info["address"]}
            ]
        }
    ]

    return await send_whatsapp_template(
        phone_number=phone_number,
        template_name="appointment_confirmation",
        components=components
    )


async def send_whatsapp_appointment_details(
    phone_number: str,
    branch_id_or_name: str = None
) -> dict:
    """
    Sends branch appointment/consultation details.
    Falls back gracefully to clinic_details until a dedicated appointment_details template is approved.
    """
    return await send_whatsapp_clinic_details(phone_number=phone_number)

