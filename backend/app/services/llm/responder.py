"""LLM-based WhatsApp response generator. Formats structured data into user-friendly messages."""

from groq import AsyncGroq

from app.core.config import settings
from app.schemas.drug import FullQueryResponse

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


RESPONSE_SYSTEM_PROMPT = """You generate WhatsApp messages for SahiDawa, an Indian medicine price comparison service.

Given structured drug data (JSON), create a clear, concise WhatsApp message showing:
1. The branded drug name, salt, and MRP
2. The cheapest generic alternative with price and savings %
3. Jan Aushadhi option if available
4. Nearest stores if available

Rules:
- Use ₹ for prices
- Keep it under 1000 characters
- Use simple formatting (no markdown, just line breaks and emojis sparingly)
- If is_narrow_therapeutic_index is true, add a warning: "⚠️ This medicine has a narrow therapeutic index. Please consult your doctor before switching."
- Always end with: "Always consult your doctor before switching medicines."
- Support Hindi if the user wrote in Hindi, otherwise English."""


async def generate_response(data: FullQueryResponse, language: str = "en") -> str:
    """Generate a user-friendly WhatsApp message from structured query results."""
    client = _get_client()
    lang_instruction = "Respond in Hindi." if language == "hi" else "Respond in English."
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"{lang_instruction}\n\nData:\n{data.model_dump_json()}",
            },
        ],
        temperature=0.3,
        max_tokens=settings.llm_max_tokens,
    )
    return response.choices[0].message.content or "Sorry, I could not generate a response."
