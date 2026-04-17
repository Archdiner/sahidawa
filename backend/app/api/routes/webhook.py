"""WhatsApp webhook endpoint — receives and processes incoming messages."""

import hashlib
import time

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.query_log import QueryLog
from app.schemas.whatsapp import WhatsAppMessage
from app.services.llm.parser import parse_drug_query
from app.services.llm.responder import generate_response
from app.services.search.drug_search import search_drugs
from app.services.whatsapp.client import send_text_message

logger = structlog.get_logger()
router = APIRouter()

WELCOME_MESSAGE = (
    "Welcome to SahiDawa!\n\n"
    "I help you find the cheapest way to buy any medicine near you.\n\n"
    "Just send me a medicine name and I'll show you:\n"
    "- Cheapest generic alternative\n"
    "- Nearest Jan Aushadhi store\n"
    "- Local chemist discounts\n\n"
    "Try it now — type any medicine name!"
)


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
    """Process incoming WhatsApp messages."""
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
    msg = WhatsAppMessage(
        from_number=msg_data["from"],
        message_id=msg_data["id"],
        text=msg_data.get("text", {}).get("body", ""),
        timestamp=msg_data["timestamp"],
        message_type=msg_data["type"],
        location=msg_data.get("location"),
    )

    start_time = time.time()

    # Handle greetings
    if msg.text.lower().strip() in ("hi", "hello", "hey", "start", "help"):
        await send_text_message(msg.from_number, WELCOME_MESSAGE)
        return {"status": "welcomed"}

    # Parse the drug query via LLM
    parsed = await parse_drug_query(msg.text)
    logger.info("query_parsed", raw=msg.text, parsed=parsed.model_dump())

    # Search the drug database
    hits = search_drugs(parsed.drug_name)

    if not hits:
        await send_text_message(
            msg.from_number,
            f"Sorry, I couldn't find '{parsed.drug_name}' in our database. "
            "Please check the spelling and try again.",
        )
        # Log the miss
        db.add(QueryLog(
            phone_hash=hashlib.sha256(msg.from_number.encode()).hexdigest(),
            raw_input=msg.text,
            parsed_drug=parsed.drug_name,
            match_found=False,
            response_time_ms=int((time.time() - start_time) * 1000),
        ))
        await db.commit()
        return {"status": "no_match"}

    # TODO: Build FullQueryResponse from hits + geo data, generate LLM response
    # For now, return raw search results as formatted text
    top = hits[0]
    response_text = (
        f"Found: {top.get('brand_name', 'Unknown')}\n"
        f"Salt: {top.get('salt_composition', 'N/A')}\n"
        f"MRP: Rs.{top.get('mrp', 'N/A')}\n\n"
        "Full generic comparison coming soon!"
    )
    await send_text_message(msg.from_number, response_text)

    # Log the query
    elapsed_ms = int((time.time() - start_time) * 1000)
    db.add(QueryLog(
        phone_hash=hashlib.sha256(msg.from_number.encode()).hexdigest(),
        raw_input=msg.text,
        parsed_drug=parsed.drug_name,
        parsed_salt=parsed.salt_composition,
        match_found=True,
        response_time_ms=elapsed_ms,
    ))
    await db.commit()

    return {"status": "responded"}
