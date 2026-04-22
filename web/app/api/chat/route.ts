import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const message = (body.message || '').trim()
    const phone = body.phone || '+919999999999'

    if (!message) {
      return NextResponse.json({ reply: 'Please send a medicine name.', language: 'en' })
    }

    // On Vercel, /api/chat routes to the Python function directly,
    // so this Next.js route won't be reached. This exists for local dev only.
    const apiBase = process.env.SAHIDAWA_API_BASE || 'http://localhost:8000'

    const response = await fetch(`${apiBase}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, phone }),
    })

    if (!response.ok) {
      return NextResponse.json(
        { reply: 'Service temporarily unavailable. Please try again.', language: 'en' },
        { status: 502 }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { reply: 'Service temporarily unavailable. Please try again.', language: 'en' },
      { status: 502 }
    )
  }
}
