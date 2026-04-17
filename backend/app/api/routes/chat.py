"""HTTP chat endpoint — test the chatbot without WhatsApp.

Usage:
  GET  /chat?q=Crocin+500&pin=226016
  POST /chat  {"message": "Crocin 500", "phone": "+91...", "pin_code": "226016"}
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chatbot import SahiDawaChatbot

router = APIRouter(prefix="/chat", tags=["chat"])

chatbot = SahiDawaChatbot()


class ChatRequest(BaseModel):
    message: str
    phone: str = "+910000000000"
    pin_code: str | None = None


class ChatReply(BaseModel):
    reply: str
    language: str


@router.get("")
async def chat_get(q: str, pin: str | None = None) -> ChatReply:
    """Quick test: GET /chat?q=Crocin+500"""
    phone = "+910000000000"
    if pin:
        chatbot.process_message(phone, pin)
    response = chatbot.process_message(phone, q)
    return ChatReply(reply=response.text, language=response.language)


@router.post("")
async def chat_post(req: ChatRequest) -> ChatReply:
    """Full test: POST /chat with body."""
    if req.pin_code:
        chatbot.process_message(req.phone, req.pin_code)
    response = chatbot.process_message(req.phone, req.message)
    return ChatReply(reply=response.text, language=response.language)
