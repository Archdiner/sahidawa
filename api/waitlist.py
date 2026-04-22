"""Vercel Python serverless function — waitlist signup."""
import json
import os

def handler(request):
    """Handles POST /api/waitlist — saves email signup."""
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': '',
        }

    if request.method != 'POST':
        return {'statusCode': 405, 'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON'})}

    email = (body.get('email') or '').strip().lower()
    name = (body.get('name') or '').strip()

    if not email or '@' not in email:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Valid email is required'}),
        }

    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SECRET_KEY')

    if supabase_url and supabase_key:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{supabase_url}/rest/v1/waitlist",
                data=json.dumps({'email': email, 'name': name or None}).encode(),
                headers={
                    'Content-Type': 'application/json',
                    'apikey': supabase_key,
                    'Authorization': f'Bearer {supabase_key}',
                    'Prefer': 'return=minimal',
                },
                method='POST',
            )
            urllib.request.urlopen(req)
        except Exception as e:
            error_msg = str(e)
            # Duplicate email — treat as success
            if '409' in error_msg or '23505' in error_msg:
                pass
            else:
                print(f"Waitlist insert error: {error_msg}")
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Failed to save. Please try again.'}),
                }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'ok': True, 'message': "You're on the list!"}),
    }
