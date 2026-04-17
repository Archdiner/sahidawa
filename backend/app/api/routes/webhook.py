"""WhatsApp webhook endpoint — receives and processes incoming messages.

Plug-and-play: once WHATSAPP_* env vars are set, this handles the full flow.
"""

import hashlib
import time

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.query_log import QueryLog
from app.services.chatbot import SahiDawaChatbot
from app.services.whatsapp.client import send_text_message

logger = structlog.get_logger()
router = APIRouter()

# Initialize chatbot (loads drug data on first message)
chatbot = SahiDawaChatbot(use_llm=bool(settings.groq_api_key))


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp webhook verification (GET)."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    """Process incoming WhatsApp messages via the chatbot engine."""
    body = await request.json()
    logger.debug("webhook_received", body=body)

    # Extract message from webhook payload
    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])

    if not messages:
        return {"status": "no_message"}

    msg_data = messages[0]
    from_number = msg_data["from"]
    msg_type = msg_data.get("type", "text")

    # Extract text and location
    text = ""
    location = None
    if msg_type == "text":
        text = msg_data.get("text", {}).get("body", "")
    elif msg_type == "interactive":
        # Button reply
        interactive = msg_data.get("interactive", {})
        if interactive.get("type") == "button_reply":
            text = interactive.get("button_reply", {}).get("title", "")
        elif interactive.get("type") == "list_reply":
            text = interactive.get("list_reply", {}).get("title", "")
    elif msg_type == "location":
        location = msg_data.get("location")
        text = "location_shared"

    if not text and not location:
        return {"status": "unsupported_message_type"}

    # Process through chatbot
    start_time = time.time()
    response = chatbot.process_message(from_number, text, location=location)
    elapsed_ms = int((time.time() - start_time) * 1000)

    # Send response via WhatsApp
    await send_text_message(from_number, response.text)

    # Log the query
    db.add(QueryLog(
        phone_hash=hashlib.sha256(from_number.encode()).hexdigest(),
        raw_input=text,
        parsed_drug=chatbot._get_session(from_number).last_query,
        match_found=chatbot._get_session(from_number).last_result.matched
        if chatbot._get_session(from_number).last_result
        else None,
        response_time_ms=elapsed_ms,
        language=response.language,
    ))
    await db.commit()

    logger.info(
        "message_processed",
        from_hash=hashlib.sha256(from_number.encode()).hexdigest()[:8],
        input=text[:50],
        response_ms=elapsed_ms,
    )

    return {"status": "responded"}
