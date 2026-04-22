"""Vercel Python serverless function — health check."""
import json


def handler(request):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'status': 'ok', 'service': 'sahidawa-api'}),
    }