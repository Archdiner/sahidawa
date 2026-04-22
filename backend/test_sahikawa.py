#!/usr/bin/env python3
"""End-to-end test suite for SahiDawa chatbot.

Tests three categories:
1. RELEVANT - drug queries that should return results
2. IRRELEVANT - queries that should be handled gracefully (not matched to drugs)
3. INCOMPLETE - queries that need clarification or extra info

Usage:
    python test_sahikawa.py              # run all tests
    python test_sahikawa.py --llm       # test with Groq LLM enabled
    python test_sahikawa.py --verbose   # show full responses
    python test_sahikawa.py --category relevant  # only relevant tests
"""

import argparse
import hashlib
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, "backend")

from app.services.chatbot import SahiDawaChatbot


@dataclass
class TestCase:
    category: str
    phone: str
    message: str
    pin_code: str | None
    expected: str
    description: str


TESTS = [
    # RELEVANT — drug queries that should return drug data or store results
    TestCase("relevant", "+919876543210", "Crocin 500", None, "match",
             "Exact brand name with strength"),
    TestCase("relevant", "+919876543210", "Dolo 650", None, "match",
             "Popular brand"),
    TestCase("relevant", "+919876543210", "Azithromycin 500", None, "match",
             "Salt name instead of brand"),
    TestCase("relevant", "+919876543210", "Augmentin 625", None, "match",
             "Brand with dose"),
    TestCase("relevant", "+919876543210", "Paracetamol 500", None, "match",
             "Generic salt name"),
    TestCase("relevant", "+919876543210", "Metformin 500", None, "match",
             "Diabetes medicine"),
    TestCase("relevant", "+919876543210", "Crocin 500", "226016", "match",
             "Drug query WITH pin code → should show stores too"),
    TestCase("relevant", "+919876543210", "Dolo 650", "110001", "match",
             "Drug query in Delhi with pin → shows stores"),
    TestCase("relevant", "+919876543210", "Cetirizine 10mg", None, "match",
             "Antihistamine query"),
    TestCase("relevant", "+919876543210", "Pantop 40", None, "match",
             "Gastric medicine (partial name)"),

    # IRRELEVANT — non-drug queries that should NOT show drug data
    TestCase("irrelevant", "+919876543210", "hi", None, "no_match",
             "Simple greeting"),
    TestCase("irrelevant", "+919876543210", "hello", None, "no_match",
             "Simple greeting"),
    TestCase("irrelevant", "+919876543210", "namaste", None, "no_match",
             "Hindi greeting"),
    TestCase("irrelevant", "+919876543210", "what is the weather today", None, "no_match",
             "Weather query"),
    TestCase("irrelevant", "+919876543210", "tell me a joke", None, "no_match",
             "Random request"),
    TestCase("irrelevant", "+919876543210", "how are you", None, "no_match",
             "Personal question"),
    TestCase("irrelevant", "+919876543210", "what can you do", None, "no_match",
             "Help question about bot"),
    TestCase("irrelevant", "+919876543210", "thanks", None, "no_match",
             "Thanks → goodbye message"),
    TestCase("irrelevant", "+919876543210", "bye", None, "no_match",
             "Farewell → goodbye message"),
    TestCase("irrelevant", "+919876543210", "IPL score", None, "no_match",
             "Sports query"),
    TestCase("irrelevant", "+919876543210", "", None, "no_match",
             "Empty message"),

    # INCOMPLETE — need clarification or extra info
    TestCase("incomplete", "+919876543210", "medicine", None, "clarification",
             "Too vague - should get clarification message"),
    TestCase("incomplete", "+919876543210", "tablet", None, "clarification",
             "Just dosage form, no drug name"),
    TestCase("incomplete", "+919876543210", "price", None, "clarification",
             "Query without drug name"),
    TestCase("incomplete", "+919876543210", "generic alternative", None, "clarification",
             "Intent without drug name"),
    TestCase("incomplete", "+919876543210", "store near me", None, "clarification",
             "Store search without pin set → asks for pin"),
    TestCase("incomplete", "+919876543210", "226016", None, "match",
             "Just pin code → sets location, shows stores"),
]


def run_test(bot: SahiDawaChatbot, tc: TestCase, verbose: bool = False) -> dict:
    phone = tc.phone
    msg = tc.message

    # Reset session for this phone to ensure clean state
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:16]
    if phone_hash in bot._sessions:
        bot._sessions[phone_hash].pin_code = None

    # Set pin code if provided (in prior message)
    if tc.pin_code:
        bot.process_message(phone, tc.pin_code)

    start = time.time()
    response = bot.process_message(phone, msg)
    elapsed = time.time() - start

    text = response.text.strip()
    text_preview = text[:100].replace("\n", " | ")

    # Determine pass/fail
    if tc.expected == "match":
        # Drug query → should show drug data OR store results
        text_lower = text.lower()
        matched = "[BRAND]" in text or ("jan aushadhi" in text_lower and "store" in text_lower)
        outcome = "PASS" if matched else "FAIL"
    elif tc.expected == "no_match":
        # Should NOT have [BRAND] + MRP (that's a drug match)
        has_drug = "[BRAND]" in text and "MRP:" in text
        has_valid_response = any(g in text.lower() for g in [
            "welcome", "namaste", "swagat", "thank you", "goodbye", "see you", "remember",
            "help", "how to", "send", "example", "medicine"
        ])
        outcome = "PASS" if (not has_drug and has_valid_response) else "FAIL"
    elif tc.expected == "clarification":
        # Should NOT show drug data, should ask for more info
        has_drug = "[BRAND]" in text and "MRP:" in text
        asks_info = any(w in text.lower() for w in ["send", "try", "example", "name", "type", "enter", "6-digit", "pin"])
        outcome = "PASS" if (not has_drug and asks_info) else "FAIL"

    return {
        "category": tc.category,
        "description": tc.description,
        "message": tc.message,
        "expected": tc.expected,
        "outcome": outcome,
        "elapsed": elapsed,
        "preview": text_preview,
        "full_text": text if verbose else None,
    }


def print_result(r: dict, verbose: bool):
    icon = "PASS" if r["outcome"] == "PASS" else "FAIL"
    cat = r["category"].upper()
    print(f"[{icon}] [{cat}] {r['description']}")
    print(f"       query: {r['message']!r}  ({r['elapsed']:.2f}s)")
    print(f"       expected: {r['expected']}, got: {r['preview']}")
    if verbose and r["full_text"]:
        print(f"       FULL RESPONSE:\n{r['full_text']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="SahiDawa end-to-end test suite")
    parser.add_argument("--llm", action="store_true", help="Use Groq LLM for parsing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full responses")
    parser.add_argument("--category", choices=["relevant", "irrelevant", "incomplete", "all"], default="all")
    parser.add_argument("--once", help="Run single test by description substring")
    args = parser.parse_args()

    use_llm = args.llm
    verbose = args.verbose

    print(f"Starting SahiDawa E2E tests (LLM={'ON' if use_llm else 'OFF'})")
    print("=" * 70)

    bot = SahiDawaChatbot(use_llm=use_llm)
    if use_llm:
        print("Groq LLM enabled")

    tests_to_run = TESTS
    if args.category != "all":
        tests_to_run = [t for t in TESTS if t.category == args.category]
    if args.once:
        tests_to_run = [t for t in tests_to_run if args.once.lower() in t.description.lower()]

    print(f"Running {len(tests_to_run)} tests...\n")

    results = []
    for tc in tests_to_run:
        r = run_test(bot, tc, verbose)
        results.append(r)
        print_result(r, verbose)

    total = len(results)
    passed = sum(1 for r in results if r["outcome"] == "PASS")
    failed = total - passed

    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"pass": 0, "fail": 0}
        if r["outcome"] == "PASS":
            by_category[cat]["pass"] += 1
        else:
            by_category[cat]["fail"] += 1

    print("=" * 70)
    print(f"SUMMARY: {passed}/{total} passed, {failed} failed")
    for cat, counts in sorted(by_category.items()):
        print(f"  {cat}: {counts['pass']} pass, {counts['fail']} fail")

    if total > 0:
        avg_lat = sum(r["elapsed"] for r in results) / total
        print(f"  Avg latency: {avg_lat:.2f}s")

    if failed > 0:
        print("\nFAILED TESTS:")
        for r in results:
            if r["outcome"] == "FAIL":
                print(f"  - [{r['category']}] {r['description']}: expected={r['expected']}, query={r['message']!r}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()