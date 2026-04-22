"""Vercel Python serverless function — chatbot endpoint."""
import json
import os
import sys

# Add backend to path
BACKEND_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_PATH)

from app.services.chatbot import SahiDawaChatbot

# Singleton bot instance (persists across warm invocations)
_bot = None

def get_bot():
    global _bot
    if _bot is None:
        _bot = SahiDawaChatbot(use_llm=bool(os.environ.get('GROQ_API_KEY')))
    return _bot


def handler(request):
    """Vercel serverless handler — handles POST /api/chat."""
    if request.method != 'POST':
        return {'statusCode': 405, 'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON'})}

    message = body.get('message', '').strip()
    phone = body.get('phone', '+919999999999')
    location = body.get('location')

    if not message:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'reply': 'Please send a medicine name.', 'language': 'en'}),
        }

    bot = get_bot()
    response = bot.process_message(phone, message, location=location)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'reply': response.text, 'language': response.language}),
    }