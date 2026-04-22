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
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum

import structlog

from app.services.drug.lookup import drug_lookup, LookupResult
from app.utils.geocoding import get_pin_code_from_coords, get_address_from_coords
from app.utils.language import detect_language

logger = structlog.get_logger()


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


LLM_PARSE_PROMPT = """You are a medicine name parser for the Indian pharmaceutical market.
Given a user's message (which may be misspelled, in Hindi/Hinglish, or informal), extract:
- drug_name: the corrected brand or generic name (fix typos like "crosin"→"Crocin", "amoxicilin"→"Amoxicillin")
- salt_composition: the active ingredient(s) if you can confidently infer it (e.g., Crocin→Paracetamol)
- strength: dosage strength if mentioned (e.g., "500mg")
- intent: one of "drug_query", "greeting", "help", "store_search", "feedback", "unknown"

If the message is NOT about a medicine (greetings, gibberish, general questions), set drug_name to null and intent accordingly.
Respond ONLY with valid JSON: {"drug_name": "...", "salt_composition": "...", "strength": "...", "intent": "..."}
If a field is unknown, set it to null. Do NOT hallucinate salt compositions — only include if confident."""


class SahiDawaChatbot:
    """Main chatbot class — stateless message processing with session management."""

    def __init__(self, use_llm: bool = False):
        self._sessions: dict[str, UserSession] = {}
        self._use_llm = use_llm
        self._groq_client = None
        drug_lookup.load()

        if use_llm:
            self._init_groq()

    def _init_groq(self):
        """Initialize sync Groq client."""
        try:
            from groq import Groq
            from app.core.config import settings
            if settings.groq_api_key:
                self._groq_client = Groq(api_key=settings.groq_api_key)
                logger.info("groq_initialized", model=settings.llm_model)
            else:
                logger.warning("groq_no_api_key")
        except ImportError:
            logger.warning("groq_not_installed")

    def _llm_parse(self, text: str) -> dict | None:
        """Parse user input via Groq LLM. Returns parsed dict or None on failure."""
        if not self._groq_client:
            return None
        try:
            from app.core.config import settings
            response = self._groq_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": LLM_PARSE_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=settings.llm_temperature,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            logger.debug("llm_parsed", input=text, result=parsed)
            return parsed
        except Exception as e:
            logger.warning("llm_parse_failed", error=str(e), input=text)
            return None

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

        # Pin code is always regex — fast path, no LLM needed
        if re.match(r"^\d{6}$", text):
            return self._handle_pin_code(session, text)

        # Try LLM parsing first for better intent + drug name extraction
        llm_result = None
        if self._use_llm:
            llm_result = self._llm_parse(text)

        if llm_result:
            llm_intent = (llm_result.get("intent") or "").lower()
            llm_drug = llm_result.get("drug_name")
            llm_salt = llm_result.get("salt_composition")

            if llm_intent == "greeting":
                return self._welcome_message(session)
            elif llm_intent == "help":
                return self._help_message(session)
            elif llm_intent == "store_search":
                return self._handle_store_search(session, text)
            elif llm_intent == "feedback":
                return self._handle_feedback(session, text)
            elif llm_intent == "unknown" and not llm_drug:
                # LLM says this isn't a drug query and has no drug name
                return self._handle_unknown(session, text)
            elif llm_drug:
                # LLM extracted a drug name — use it (with salt hint + strength)
                llm_strength = llm_result.get("strength")
                return self._handle_drug_query(
                    session, text,
                    llm_drug_name=llm_drug,
                    llm_salt=llm_salt,
                    llm_strength=llm_strength,
                )

        # Fallback: regex-based intent detection
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
        elif intent == Intent.UNKNOWN:
            return self._handle_unknown(session, text)
        else:
            return self._handle_drug_query(session, text)

    def _detect_intent(self, text: str) -> Intent:
        text_lower = text.lower().strip()

        # Empty
        if not text_lower:
            return Intent.UNKNOWN

        # Greetings (partial match since non-LLM can't fix typos)
        greetings = {"hi", "hello", "hey", "start", "namaste", "namaskar", "hii", "hiii", "good morning", "good evening", "good night"}
        if any(g in text_lower for g in greetings):
            return Intent.GREETING

        # Help
        if any(h in text_lower for h in ["help", "kya hai", "madad", "sahayata", "what can you do", "how to use", "instructions"]):
            return Intent.HELP

        # Store search
        store_triggers = ["store", "dukan", "shop", "kendra", "jan aushadhi", "janaushadhi", "nearest", "pharmacy", "medical store"]
        if any(t in text_lower for t in store_triggers):
            return Intent.STORE_SEARCH

        # Pin code (6-digit number)
        if re.match(r"^\d{6}$", text_lower):
            return Intent.LOCATION

        # Feedback / thanks / farewell
        feedback_words = ["thanks", "thank you", "dhanyavad", "shukriya", "wrong", "galat", "bye", "goodbye", "see you", "exit"]
        if any(w in text_lower for w in feedback_words):
            return Intent.FEEDBACK

        # Personal / non-drug queries — likely NOT a drug query
        # These phrases suggest the user is not looking for medicine info
        non_drug_triggers = [
            "weather", "joke", "news", "score", "cricket", "how are you",
            "your name", "who are you", "where are you", "when is",
            "what is the", "whose", "which is the best", "tell me about",
        ]
        if any(nd in text_lower for nd in non_drug_triggers):
            return Intent.UNKNOWN

        # Default: treat as drug query
        return Intent.DRUG_QUERY

    def _is_vague_drug_query(self, text: str) -> bool:
        """Check if query is too generic/non-specific to be a valid drug search."""
        text_lower = text.lower().strip()

        # Single generic words that aren't valid drug queries
        generic_words = {
            "tablet", "capsule", "syrup", "injection", "ointment", "drops",
            "cream", "lotion", "gel", "solution", "powder", "suppository",
            "medicine", "med", "pharmacy", "drug", "tab", "cap", "syp",
            "generic", "alternative", "substitute", "price", "cost",
            "cheap", "affordable", "store", "shop",
        }
        if text_lower in generic_words:
            return True

        # Short ambiguous queries (2-3 chars likely to match random things)
        if len(text_lower) <= 3:
            return True

        # Single common words that happen to match brand names in DB
        if text_lower in {"pan", "lab", "cor", "zip", "zip", "cid", "aid", "dol", "gel"}:
            return True

        return False

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

    def _handle_drug_query(
        self,
        session: UserSession,
        text: str,
        llm_drug_name: str | None = None,
        llm_salt: str | None = None,
        llm_strength: str | None = None,
    ) -> ChatResponse:
        """Main drug query handler — the core product flow."""
        session.query_count += 1
        session.last_query = text

        # If LLM is not being used, check for vague queries before doing DB search
        parsed_text = self._parse_drug_name(text) if not llm_drug_name else text
        if not llm_drug_name and self._is_vague_drug_query(parsed_text):
            return ChatResponse(
                text=(
                    f"I couldn't find '{text}' as a valid medicine name.\n\n"
                    "Please send the actual brand or salt name.\n"
                    "Examples: Crocin 500, Dolo 650, Augmentin 625, Paracetamol\n\n"
                    "Type 'help' for more options."
                ),
            )

        # Use LLM-parsed name if available, otherwise regex fallback
        if llm_drug_name:
            # If LLM gave us strength, append it for better search matching
            drug_name = llm_drug_name
            search_query = f"{llm_drug_name} {llm_strength}" if llm_strength else llm_drug_name
        else:
            drug_name = self._parse_drug_name(text)
            search_query = drug_name

        # Look up drug and generics (with salt hint from LLM)
        result = drug_lookup.lookup(
            search_query, pin_code=session.pin_code, salt_hint=llm_salt
        )
        session.last_result = result

        # If search_query didn't match, try just the drug name (without strength)
        if not result.matched and search_query != drug_name:
            result = drug_lookup.lookup(
                drug_name, pin_code=session.pin_code, salt_hint=llm_salt
            )
            session.last_result = result

        # If LLM name didn't match, try the salt hint directly
        if not result.matched and llm_salt:
            result = drug_lookup.lookup(
                llm_salt, pin_code=session.pin_code
            )
            session.last_result = result

        # If still no match, try regex-cleaned name as last resort
        if not result.matched and llm_drug_name:
            fallback_name = self._parse_drug_name(text)
            if fallback_name != llm_drug_name:
                result = drug_lookup.lookup(
                    fallback_name, pin_code=session.pin_code
                )
                session.last_result = result

        if not result.matched:
            # Try with strength stripped
            cleaned = re.sub(r"\d+\s*mg", "", drug_name).strip()
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

    def _handle_unknown(self, session: UserSession, text: str) -> ChatResponse:
        """Handle messages we can't identify as drug queries."""
        text_lower = text.lower().strip()

        # Check if it looks like a non-drug question
        non_drug_phrases = [
            "weather", "joke", "news", "score", "cricket", "how are you",
            "your name", "who are you", "where are you", "when is the",
            "what is the best", "whose", "tell me about", "latest",
            "price of", "cost of", "worth", "value of",
        ]
        looks_like_question = text_lower.startswith(("what", "who", "where", "when", "why", "how", "whose", "which", "tell", "is ", "are ", "do ", "does ", "can ")) and len(text_lower) > 15

        if any(nd in text_lower for nd in non_drug_phrases) or looks_like_question:
            return ChatResponse(
                text=(
                    "I'm a medicine price discovery bot — I find cheap generic alternatives for medicines.\n\n"
                    "Just send me a medicine name and I'll show you the cheapest options!\n"
                    "Example: Crocin, Dolo 650, Augmentin, Paracetamol 500\n\n"
                    "Type 'help' for more options."
                ),
            )

        # Empty message
        if not text_lower:
            return ChatResponse(
                text="Please send a medicine name to search!\n\nExample: Crocin 500, Dolo 650",
            )

        # Generic unknown
        return ChatResponse(
            text=(
                "I didn't quite understand that.\n\n"
                "Send me a medicine name and I'll find the cheapest generic.\n"
                "Example: Crocin 500, Augmentin 625, Dolo 650\n\n"
                "Type 'help' for more options."
            ),
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
        lines.append(f"[BRAND] {drug.brand_name}")
        lines.append(f"Salt: {drug.salt_name} {drug.strength}")
        lines.append(f"MRP: Rs.{drug.mrp:.2f} ({drug.pack_size})")
        lines.append(f"By: {drug.manufacturer}")
        lines.append("")

        # Cheapest generic
        if result.cheapest:
            c = result.cheapest
            lines.append("[CHEAPEST GENERIC]")
            lines.append(f"{c.brand_name}")
            lines.append(f"Price: Rs.{c.mrp:.2f} ({c.pack_size})")
            lines.append(f"By: {c.manufacturer}")
            lines.append(f"You save: Rs.{c.savings_amount:.2f} ({c.savings_percent:.0f}%)")
            lines.append("")

            # Top 5 alternatives
            if len(result.generics) > 1:
                top_n = min(5, len(result.generics))
                lines.append(f"[TOP {top_n} OF {result.total_alternatives} ALTERNATIVES]:")
                for i, g in enumerate(result.generics[:top_n]):
                    lines.append(f"{i+1}. {g.brand_name} - Rs.{g.mrp:.2f}")
                lines.append("")
        else:
            lines.append("[INFO] No cheaper alternatives found for this exact formulation.")
            lines.append("")

        # NPPA ceiling price
        if result.ceiling_price:
            cp = result.ceiling_price
            lines.append(f"[GOVT CEILING PRICE] ({cp.dosage_form} {cp.strength}): Rs.{cp.ceiling_price:.2f}/unit")
            lines.append("")

        # Jan Aushadhi stores
        if result.nearby_stores:
            lines.append("[JAN AUSHADHI STORES NEAR YOU]:")
            for s in result.nearby_stores[:3]:
                lines.append(f"  - {s.store_code}")
                lines.append(f"    {s.address}")
                if s.phone:
                    lines.append(f"    Phone: {s.phone}")
            lines.append("")
        elif session.pin_code:
            lines.append("[INFO] No Jan Aushadhi store found for your pin code.")
            lines.append("")
        else:
            lines.append("[TIP] Send your pin code to find Jan Aushadhi stores near you.")
            lines.append("")

        # Disclaimer
        lines.append("[WARNING] Always consult your doctor before switching medicines.")

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
                lines = [f"[JAN AUSHADHI STORES NEAR {session.pin_code}]:\n"]
                for i, s in enumerate(stores[:5], 1):
                    lines.append(f"{i}. {s.store_code}")
                    lines.append(f"   {s.address}")
                    lines.append(f"   {s.district}, {s.state} - {s.pin_code}")
                    if s.phone:
                        lines.append(f"   Phone: {s.phone}")
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
            lines = [f"[INFO] Found {len(stores)} Jan Aushadhi store(s) near {pin}:\n"]
            for i, s in enumerate(stores[:5], 1):
                lines.append(f"{i}. {s.store_code}")
                lines.append(f"   {s.address}")
                lines.append(f"   {s.district}, {s.state}")
                if s.phone:
                    lines.append(f"   Phone: {s.phone}")
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
        """Handle WhatsApp location sharing — reverse geocode to pin code."""
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat and lng:
            pin_code = get_pin_code_from_coords(lat, lng)
            address = get_address_from_coords(lat, lng)

            if pin_code:
                session.pin_code = pin_code
                stores = drug_lookup.find_stores_by_pin(pin_code)
                store_msg = f"Found {len(stores)} Jan Aushadhi store(s) near your location." if stores else "No Jan Aushadhi stores found near your location."

                location_info = f"Your location: {address}" if address else None

                lines = [
                    "[LOCATION RECEIVED]",
                    location_info if location_info else None,
                    f"Pin code: {pin_code}",
                    store_msg,
                    "",
                    "Send any medicine name to search!",
                ]
                lines = [l for l in lines if l]
                return ChatResponse(text="\n".join(lines))
            else:
                return ChatResponse(
                    text=(
                        "[LOCATION] Could not determine your pin code from coordinates.\n"
                        "Please send your 6-digit pin code manually.\n\n"
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
        if any(w in text_lower for w in ["bye", "goodbye", "see you", "exit"]):
            return ChatResponse(
                text=(
                    "Thank you for using SahiDawa!\n\n"
                    "Remember: always consult your doctor before switching medicines.\n"
                    "Send any medicine name anytime to search again."
                ),
            )
        return ChatResponse(
            text="Thank you for using SahiDawa! Send another medicine name anytime.",
        )
