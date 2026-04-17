#!/usr/bin/env python3
"""Interactive CLI test harness for the SahiDawa chatbot.

Simulates WhatsApp conversations locally — no services needed.
Just run: python test_chatbot.py

Usage:
  python test_chatbot.py              # Interactive mode
  python test_chatbot.py --demo       # Run demo conversation
  python test_chatbot.py --batch      # Process queries from stdin
"""

import sys
import time

sys.path.insert(0, ".")
from app.services.chatbot import SahiDawaChatbot


def interactive_mode():
    """Interactive chat simulation."""
    bot = SahiDawaChatbot()
    phone = "+919999999999"

    print("=" * 60)
    print("  SahiDawa Chatbot — Local Test Mode")
    print("  Type medicine names, pin codes, or 'quit' to exit")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        start = time.time()
        response = bot.process_message(phone, user_input)
        elapsed = (time.time() - start) * 1000

        print(f"\nBot ({elapsed:.0f}ms):")
        print(response.text)
        print()


def demo_mode():
    """Run a scripted demo conversation."""
    bot = SahiDawaChatbot()
    phone = "+919876543210"

    demo_messages = [
        "Hi",
        "Crocin 500",
        "226016",
        "Augmentin 625",
        "Dolo 650",
        "Azithral",
        "Pantoprazole",
        "store",
        "Metformin",
        "paracetamol",
        "help",
        "thanks",
    ]

    print("=" * 60)
    print("  SahiDawa Chatbot — Demo Conversation")
    print("=" * 60)

    for msg in demo_messages:
        print(f"\n{'─' * 60}")
        print(f"User: {msg}")
        print(f"{'─' * 60}")

        start = time.time()
        response = bot.process_message(phone, msg)
        elapsed = (time.time() - start) * 1000

        print(f"\nBot ({elapsed:.0f}ms):")
        print(response.text)

    print(f"\n{'=' * 60}")
    print("Demo complete!")


def batch_mode():
    """Process queries from stdin, one per line."""
    bot = SahiDawaChatbot()
    phone = "+919999999999"

    for line in sys.stdin:
        query = line.strip()
        if not query:
            continue
        response = bot.process_message(phone, query)
        print(f"Q: {query}")
        print(f"A: {response.text}")
        print("---")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo_mode()
    elif "--batch" in sys.argv:
        batch_mode()
    else:
        interactive_mode()
