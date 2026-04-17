"""SahiDawa chatbot — complete conversation engine.

Handles the full message flow:
  1. Detect intent (greeting, drug query, location, help)
  2. Parse drug name from natural language (LLM or regex fallback)
  3. Look up drug, find generics, find stores
  4. Format response as WhatsApp-friendly text
  5. Track conversation state per user (location, last query)

Designed to work in two modes:
  - With LLM (Groq): better input parsing, Hindi support, natural responses
  - Without LLM (fallback): regex-based parsing, template responses — fully functional
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum

from app.services.drug.lookup import drug_lookup, LookupResult
from app.utils.language import detect_language


class Intent(Enum):
    GREETING = "greeting"
    DRUG_QUERY = "drug_query"
    LOCATION = "location"
    STORE_SEARCH = "store_search"
    HELP = "help"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


@dataclass
class UserSession:
    """Per-user conversation state."""
    phone_hash: str
    pin_code: str | None = None
    last_query: str | None = None
    last_result: LookupResult | None = None
    language: str = "en"
    query_count: int = 0


@dataclass
class ChatResponse:
    """Bot response to send back."""
    text: str
    buttons: list[dict] = field(default_factory=list)
    language: str = "en"


class SahiDawaChatbot:
    """Main chatbot class — stateless message processing with session management."""

    def __init__(self, use_llm: bool = False):
        self._sessions: dict[str, UserSession] = {}
        self._use_llm = use_llm
        drug_lookup.load()

    def _get_session(self, phone: str) -> UserSession:
        phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:16]
        if phone_hash not in self._sessions:
            self._sessions[phone_hash] = UserSession(phone_hash=phone_hash)
        return self._sessions[phone_hash]

    def process_message(self, phone: str, text: str, location: dict | None = None) -> ChatResponse:
        """Process an incoming message and return a response."""
        session = self._get_session(phone)
        session.language = detect_language(text)
        text = text.strip()

        # Handle location sharing
        if location:
            return self._handle_location(session, location)

        # Detect intent
        intent = self._detect_intent(text)

        if intent == Intent.GREETING:
            return self._welcome_message(session)
        elif intent == Intent.HELP:
            return self._help_message(session)
        elif intent == Intent.STORE_SEARCH:
            return self._handle_store_search(session, text)
        elif intent == Intent.LOCATION:
            return self._handle_pin_code(session, text)
        elif intent == Intent.FEEDBACK:
            return self._handle_feedback(session, text)
        else:
            return self._handle_drug_query(session, text)

    def _detect_intent(self, text: str) -> Intent:
        text_lower = text.lower().strip()

        # Greetings
        greetings = {"hi", "hello", "hey", "start", "namaste", "namaskar", "hii", "hiii"}
        if text_lower in greetings:
            return Intent.GREETING

        # Help
        if text_lower in {"help", "?", "kya hai", "madad", "sahayata"}:
            return Intent.HELP

        # Store search
        store_triggers = ["store", "dukan", "shop", "kendra", "jan aushadhi", "janaushadhi", "nearest"]
        if any(t in text_lower for t in store_triggers):
            return Intent.STORE_SEARCH

        # Pin code (6-digit number)
        if re.match(r"^\d{6}$", text_lower):
            return Intent.LOCATION

        # Feedback
        feedback_words = ["thanks", "thank you", "dhanyavad", "shukriya", "wrong", "galat"]
        if any(w in text_lower for w in feedback_words):
            return Intent.FEEDBACK

        # Default: treat as drug query
        return Intent.DRUG_QUERY

    def _welcome_message(self, session: UserSession) -> ChatResponse:
        if session.language == "hi":
            return ChatResponse(
                text=(
                    "SahiDawa mein aapka swagat hai!\n\n"
                    "Main aapko kisi bhi dawai ka sabse sasta generic "
                    "alternative dhundne mein madad karta hoon.\n\n"
                    "Bas dawai ka naam bhejein!\n\n"
                    "Udaharan: Crocin, Augmentin, Dolo 650"
                ),
                language="hi",
            )
        return ChatResponse(
            text=(
                "Welcome to SahiDawa!\n\n"
                "I help you find the cheapest generic alternative "
                "for any medicine in India.\n\n"
                "Just send me a medicine name and I'll show you:\n"
                "- Cheapest generic alternative\n"
                "- How much you can save\n"
                "- Nearest Jan Aushadhi store\n\n"
                "Try it now! Send any medicine name.\n"
                "Example: Crocin, Augmentin, Dolo 650"
            ),
        )

    def _help_message(self, session: UserSession) -> ChatResponse:
        return ChatResponse(
            text=(
                "How to use SahiDawa:\n\n"
                "1. Send any medicine name\n"
                "   Example: Crocin 500\n\n"
                "2. Send your pin code to find nearby Jan Aushadhi stores\n"
                "   Example: 226016\n\n"
                "3. Type 'store' to search for Jan Aushadhi stores\n\n"
                "I support English and Hindi!\n\n"
                "Note: Always consult your doctor before switching medicines."
            ),
        )

    def _handle_drug_query(self, session: UserSession, text: str) -> ChatResponse:
        """Main drug query handler — the core product flow."""
        session.query_count += 1
        session.last_query = text

        # Parse the drug name (regex fallback — LLM can be added on top)
        drug_name = self._parse_drug_name(text)

        # Look up drug and generics
        result = drug_lookup.lookup(drug_name, pin_code=session.pin_code)
        session.last_result = result

        if not result.matched:
            # Try with cleaned input
            cleaned = re.sub(r"\d+\s*mg", "", text).strip()
            if cleaned and cleaned != drug_name:
                result = drug_lookup.lookup(cleaned, pin_code=session.pin_code)
                session.last_result = result

        if not result.matched:
            return ChatResponse(
                text=(
                    f"Sorry, I couldn't find '{text}' in our database.\n\n"
                    "Tips:\n"
                    "- Check the spelling\n"
                    "- Try the brand name (e.g., 'Crocin' not 'fever medicine')\n"
                    "- Try just the salt name (e.g., 'Paracetamol')\n\n"
                    "Send another medicine name to try again."
                ),
            )

        return ChatResponse(
            text=self._format_drug_response(result, session),
            language=session.language,
        )

    def _parse_drug_name(self, text: str) -> str:
        """Extract drug name from user message (regex fallback)."""
        text = text.strip()

        # Remove common prefixes users add
        prefixes = [
            r"^(?:price|cost|rate|keemat|daam)\s+(?:of|ka|ki)?\s*",
            r"^(?:generic|alternative|substitute)\s+(?:of|for|ka|ki)?\s*",
            r"^(?:find|search|show|check|batao|dikhao)\s*",
            r"^(?:what is|whats|kya hai)\s+(?:the\s+)?(?:price|cost|generic)\s+(?:of|for)?\s*",
        ]
        for pattern in prefixes:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Remove trailing noise
        suffixes = [
            r"\s+(?:ka|ki|ke)\s+(?:price|daam|keemat|generic|alternative).*$",
            r"\s+(?:price|cost|rate|tablet|tab|cap|capsule|syrup)s?\s*$",
        ]
        for pattern in suffixes:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        return text if text else "unknown"

    def _format_drug_response(self, result: LookupResult, session: UserSession) -> str:
        """Format a complete drug lookup result as a WhatsApp message."""
        drug = result.drug
        lines = []

        # Header: branded drug info
        lines.append(f"💊 {drug.brand_name}")
        lines.append(f"Salt: {drug.salt_name} {drug.strength}")
        lines.append(f"MRP: ₹{drug.mrp:.2f} ({drug.pack_size})")
        lines.append(f"By: {drug.manufacturer}")
        lines.append("")

        # Cheapest generic
        if result.cheapest:
            c = result.cheapest
            lines.append("✅ CHEAPEST GENERIC")
            lines.append(f"{c.brand_name}")
            lines.append(f"Price: ₹{c.mrp:.2f} ({c.pack_size})")
            lines.append(f"By: {c.manufacturer}")
            lines.append(f"You save: ₹{c.savings_amount:.2f} ({c.savings_percent:.0f}%)")
            lines.append("")

            # Top 5 alternatives
            if len(result.generics) > 1:
                top_n = min(5, len(result.generics))
                lines.append(f"📋 TOP {top_n} OF {result.total_alternatives} ALTERNATIVES:")
                for i, g in enumerate(result.generics[:top_n]):
                    lines.append(f"{i+1}. {g.brand_name} — ₹{g.mrp:.2f}")
                lines.append("")
        else:
            lines.append("ℹ️ No cheaper alternatives found for this exact formulation.")
            lines.append("")

        # NPPA ceiling price
        if result.ceiling_price:
            cp = result.ceiling_price
            lines.append(f"🏛️ Govt ceiling price ({cp.dosage_form} {cp.strength}): ₹{cp.ceiling_price:.2f}/unit")
            lines.append("")

        # Jan Aushadhi stores
        if result.nearby_stores:
            lines.append("🏥 JAN AUSHADHI STORES NEAR YOU:")
            for s in result.nearby_stores[:3]:
                lines.append(f"📍 {s.store_code}")
                lines.append(f"   {s.address}")
                if s.phone:
                    lines.append(f"   📞 {s.phone}")
            lines.append("")
        elif session.pin_code:
            lines.append("🏥 No Jan Aushadhi store found for your pin code.")
            lines.append("")
        else:
            lines.append("📍 Send your pin code to find Jan Aushadhi stores near you.")
            lines.append("")

        # Disclaimer
        lines.append("⚠️ Always consult your doctor before switching medicines.")

        return "\n".join(lines)

    def _handle_store_search(self, session: UserSession, text: str) -> ChatResponse:
        """Handle store search requests."""
        # Try to extract pin code from the message
        pin_match = re.search(r"\d{6}", text)
        if pin_match:
            return self._handle_pin_code(session, pin_match.group(0))

        if session.pin_code:
            stores = drug_lookup.find_stores_by_pin(session.pin_code)
            if stores:
                lines = [f"🏥 JAN AUSHADHI STORES NEAR {session.pin_code}:\n"]
                for i, s in enumerate(stores[:5], 1):
                    lines.append(f"{i}. {s.store_code}")
                    lines.append(f"   {s.address}")
                    lines.append(f"   {s.district}, {s.state} - {s.pin_code}")
                    if s.phone:
                        lines.append(f"   📞 {s.phone}")
                    lines.append("")
                return ChatResponse(text="\n".join(lines))
            else:
                return ChatResponse(
                    text=f"No Jan Aushadhi stores found near pin code {session.pin_code}.\nTry a nearby pin code.",
                )

        return ChatResponse(
            text="To find Jan Aushadhi stores near you, please send your 6-digit pin code.\n\nExample: 226016",
        )

    def _handle_pin_code(self, session: UserSession, text: str) -> ChatResponse:
        pin_match = re.search(r"\d{6}", text)
        if not pin_match:
            return ChatResponse(text="Please send a valid 6-digit pin code.\nExample: 226016")

        pin = pin_match.group(0)
        session.pin_code = pin

        stores = drug_lookup.find_stores_by_pin(pin)
        if stores:
            lines = [f"📍 Found {len(stores)} Jan Aushadhi store(s) near {pin}:\n"]
            for i, s in enumerate(stores[:5], 1):
                lines.append(f"{i}. {s.store_code}")
                lines.append(f"   {s.address}")
                lines.append(f"   {s.district}, {s.state}")
                if s.phone:
                    lines.append(f"   📞 {s.phone}")
                lines.append("")
            lines.append("Your location is saved. Future medicine queries will show nearby stores.")
            lines.append("\nSend any medicine name to search!")
            return ChatResponse(text="\n".join(lines))
        else:
            session.pin_code = pin  # Save anyway for area search
            return ChatResponse(
                text=(
                    f"No Jan Aushadhi store found at pin code {pin}.\n"
                    "I've saved your location and will search nearby areas.\n\n"
                    "Send any medicine name to search!"
                ),
            )

    def _handle_location(self, session: UserSession, location: dict) -> ChatResponse:
        """Handle WhatsApp location sharing."""
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat and lng:
            # For now, just acknowledge — PostGIS queries need the DB
            return ChatResponse(
                text=(
                    "📍 Location received! For best results with our current system, "
                    "please also send your 6-digit pin code.\n\n"
                    "Example: 226016"
                ),
            )
        return ChatResponse(text="Couldn't read your location. Please send your pin code instead.")

    def _handle_feedback(self, session: UserSession, text: str) -> ChatResponse:
        text_lower = text.lower()
        if any(w in text_lower for w in ["wrong", "galat", "incorrect"]):
            return ChatResponse(
                text=(
                    "Sorry about that! Our database covers 2.4 lakh medicines but "
                    "some entries may be outdated.\n\n"
                    "Please try:\n"
                    "- A different spelling\n"
                    "- The exact brand name from your prescription\n"
                    "- The salt/molecule name\n\n"
                    "Your feedback helps us improve!"
                ),
            )
        return ChatResponse(
            text="Thank you for using SahiDawa! Send another medicine name anytime.",
        )
