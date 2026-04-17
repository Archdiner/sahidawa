"""LLM-based drug query parser. Normalizes messy user input into structured drug queries."""

import json

from groq import AsyncGroq

from app.core.config import settings
from app.schemas.drug import ParsedDrugQuery

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


PARSE_SYSTEM_PROMPT = """You are a medicine name parser for the Indian pharmaceutical market.
Given a user's message (which may be misspelled, in Hindi, or informal), extract:
- drug_name: the brand or generic name they're referring to
- salt_composition: the active ingredient(s) if you can infer it
- strength: dosage strength if mentioned (e.g., "500mg")
- dosage_form: tablet, capsule, syrup, etc. if mentioned

Respond ONLY with valid JSON matching this schema:
{"drug_name": "...", "salt_composition": "...", "strength": "...", "dosage_form": "..."}

If a field is unknown, set it to null. Do NOT hallucinate salt compositions — only include if you are confident."""


async def parse_drug_query(raw_input: str) -> ParsedDrugQuery:
    """Parse a raw user message into a structured drug query using LLM."""
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": raw_input},
        ],
        temperature=settings.llm_temperature,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return ParsedDrugQuery(
        drug_name=data.get("drug_name", raw_input),
        salt_composition=data.get("salt_composition"),
        strength=data.get("strength"),
        dosage_form=data.get("dosage_form"),
    )
