"""WhatsApp Cloud API client for sending messages."""

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def send_text_message(to: str, body: str) -> dict:
    """Send a text message via WhatsApp Cloud API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.whatsapp_api_url,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            },
        )
        response.raise_for_status()
        data = response.json()
        logger.info("whatsapp_message_sent", to=to, message_id=data.get("messages", [{}])[0].get("id"))
        return data


async def send_interactive_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    """Send an interactive button message."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.whatsapp_api_url,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                            for b in buttons[:3]
                        ]
                    },
                },
            },
        )
        response.raise_for_status()
        return response.json()
