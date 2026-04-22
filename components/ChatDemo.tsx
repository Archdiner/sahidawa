'use client'
import { useEffect, useRef, useState } from 'react'

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
  time: string
}

function formatTime() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
}

function formatBotText(text: string): React.ReactNode[] {
  const lines = text.split('\n')
  const nodes: React.ReactNode[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Empty line → small gap
    if (!line.trim()) {
      nodes.push(<span key={i} className="msg-gap" />)
      continue
    }

    // Section headers: [CHEAPEST GENERIC], [TOP 5 OF...], [GOVT...], [JAN...], [TIP], [WARNING]
    if (line.startsWith('[')) {
      if (line.startsWith('[BRAND]')) {
        nodes.push(<strong key={i} className="msg-brand">{line.replace('[BRAND] ', '')}</strong>)
      } else if (line.startsWith('[WARNING]')) {
        nodes.push(<span key={i} className="msg-warning">{line.replace('[WARNING] ', '')}</span>)
      } else if (line.startsWith('[TIP]')) {
        nodes.push(<span key={i} className="msg-tip">{line.replace('[TIP] ', '')}</span>)
      } else {
        nodes.push(<span key={i} className="msg-section">{line.replace(/^\[|\]$/g, '').replace(']:$', '')}</span>)
      }
      continue
    }

    // "You save: X (Y%)" → green savings badge
    if (line.startsWith('You save:')) {
      nodes.push(<span key={i} className="msg-save">{line}</span>)
      continue
    }

    // Numbered list items: "1. Babymol 500mg..."
    const numMatch = line.match(/^(\d+\.\s)(.+)/)
    if (numMatch) {
      nodes.push(
        <span key={i} className="msg-list-item">
          <span className="msg-list-num">{numMatch[1]}</span>{numMatch[2]}
        </span>
      )
      continue
    }

    // Store lines: "  - ..." or "  1. Store..."
    if (line.startsWith('  ')) {
      nodes.push(<span key={i} className="msg-store">{line.trim()}</span>)
      continue
    }

    // Key: value pairs — Salt, MRP, By, Price
    const kvMatch = line.match(/^(Salt|MRP|By|Price):\s*(.+)/)
    if (kvMatch) {
      nodes.push(
        <span key={i} className="msg-kv">
          <strong>{kvMatch[1]}:</strong> {kvMatch[2]}
        </span>
      )
      continue
    }

    // Default
    nodes.push(<span key={i} className="msg-line">{line}</span>)
  }

  return nodes
}

export default function ChatDemo() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const msgsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const el = msgsRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  async function send(text: string) {
    if (!text.trim()) return
    const userMsg: Message = { id: Date.now(), text, sender: 'user', time: formatTime() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/_/backend/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, phone: '+919999999999' }),
      })
      const data = await res.json()
      const botMsg: Message = {
        id: Date.now() + 1,
        text: data.reply || "Sorry, something went wrong. Please try again.",
        sender: 'bot',
        time: formatTime(),
      }
      setMessages(prev => [...prev, botMsg])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "Sorry, the demo is temporarily unavailable. Please try again.",
        sender: 'bot',
        time: formatTime(),
      }])
    } finally {
      setLoading(false)
    }
  }

  const QUICK_PROMPTS = ['Crocin 500', 'Dolo 650', 'Paracetamol 500', 'Metformin 500']

  return (
    <section className="demo-section" id="demo" ref={ref}>
      <div className="demo-header container">
        <p className="demo-eyebrow">Live demo</p>
        <h2 className="demo-title">See it work. Right now.</h2>
        <p className="demo-sub">Branded, generic, misspelled — type anything. Real data, real prices.</p>
      </div>
      <div className="container">
        <div className={`chat-wrap sr ${visible ? 'v' : ''}`}>
          <div className="chat-window">
            <div className="chat-header">
              <div className="ch-ava">S</div>
              <div>
                <div className="ch-name">SahiDawa</div>
                <div className="ch-status">online</div>
              </div>
            </div>
            <div className="chat-msgs" ref={msgsRef}>
              {messages.length === 0 && (
                <div className="chat-empty">
                  <p>Send a medicine name to get started.</p>
                  <p>Try one of these:</p>
                  <div className="quick-prompts">
                    {QUICK_PROMPTS.map(q => (
                      <button key={q} className="quick-btn" onClick={() => send(q)}>{q}</button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map(m => (
                <div key={m.id} className={`cm ${m.sender}`}>
                  <div className="cm-text">{m.sender === 'bot' ? formatBotText(m.text) : m.text}</div>
                  <div className="cm-time">{m.time}</div>
                </div>
              ))}
              {loading && (
                <div className="cm bot typing">
                  <div className="typing-dots">
                    <span /><span /><span />
                  </div>
                </div>
              )}
            </div>
            <div className="chat-input-bar">
              <input
                className="chat-input"
                placeholder="Type a medicine name..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    send(input)
                  }
                }}
              />
              <button
                className="send-btn"
                onClick={() => send(input)}
                disabled={loading || !input.trim()}
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}