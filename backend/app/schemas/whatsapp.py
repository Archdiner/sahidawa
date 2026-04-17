from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    """Parsed incoming WhatsApp message."""

    from_number: str
    message_id: str
    text: str
    timestamp: str
    message_type: str = "text"
    location: dict | None = None
