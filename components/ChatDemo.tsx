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
  return text.split('\n').map((line, i) => {
    if (!line) return <br key={i} />
    if (line.startsWith('[BRAND]')) return <strong key={i} className="msg-brand">{line.replace('[BRAND] ', '')}</strong>
    if (line.startsWith('[CHEAPEST GENERIC]') || line.startsWith('[JAN') || line.startsWith('[WARNING]') || line.startsWith('[GOVT')) {
      return <span key={i} className="msg-section">{line}</span>
    }
    if (line.startsWith('Save')) return <span key={i} className="msg-save">{line}</span>
    if (line.startsWith('  -')) return <span key={i} className="msg-store">{line.trim()}</span>
    // Bold key
    const boldMatch = line.match(/^(Brand|Salt|MRP|By|Price|You save):?\s*/)
    if (boldMatch) {
      const after = line.slice(boldMatch[0].length)
      return (
        <span key={i}>
          <strong>{boldMatch[0]}</strong>{after}
        </span>
      )
    }
    return <span key={i}>{line}</span>
  })
}

export default function ChatDemo() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(text: string) {
    if (!text.trim()) return
    const userMsg: Message = { id: Date.now(), text, sender: 'user', time: formatTime() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
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
      <div className="container">
        <div className={`demo-context sr ${visible ? 'v' : ''}`}>
          <h2 className="demo-title">See it work. Right now.</h2>
          <p>
            Type any medicine name — branded, generic, misspelled — and get an
            instant price comparison with real data from 62,000+ medicines.
          </p>
          <div className="stats">
            {[
              { num: '62,000+', label: 'Medicines mapped' },
              { num: '10,000+', label: 'Jan Aushadhi stores' },
              { num: '<3s', label: 'Response time' },
            ].map(s => (
              <div key={s.label} className="stat-item">
                <div className="stat-num">{s.num}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className={`chat-wrap sr ${visible ? 'v' : ''}`} style={{ transitionDelay: '0.1s' }}>
          <div className="chat-window">
            <div className="chat-header">
              <div className="ch-ava">S</div>
              <div>
                <div className="ch-name">SahiDawa</div>
                <div className="ch-status">online</div>
              </div>
            </div>
            <div className="chat-msgs">
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
              <div ref={bottomRef} />
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
      <style>{`
        .demo-section {
          padding: clamp(64px, 9vh, 100px) 0;
        }
        .demo-section .container {
          display: grid;
          grid-template-columns: 1fr 420px;
          gap: 64px;
          align-items: end;
          max-width: 1140px;
          margin: 0 auto;
          padding: 0 clamp(24px, 5vw, 64px);
        }
        .demo-title {
          font-family: var(--serif);
          font-size: clamp(28px, 3.4vw, 42px);
          font-weight: 700;
          letter-spacing: -1px;
          line-height: 1.1;
          margin-bottom: 16px;
        }
        .demo-context p {
          font-size: 14px;
          color: var(--text-3);
          line-height: 1.7;
          margin-bottom: 24px;
          max-width: 420px;
        }
        .stats { display: flex; gap: 36px; flex-wrap: wrap; }
        .stat-item { }
        .stat-num {
          font-family: var(--serif);
          font-size: 32px;
          font-weight: 700;
          letter-spacing: -1px;
        }
        .stat-label { font-size: 12px; color: var(--text-3); margin-top: 2px; }

        /* ── Chat Window ── */
        .chat-wrap { }
        .chat-window {
          background: #fff;
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 0 16px 48px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06);
          border: 1px solid var(--line);
          display: flex;
          flex-direction: column;
          height: 520px;
        }
        .chat-header {
          background: #075E54;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #fff;
        }
        .ch-ava {
          width: 32px; height: 32px;
          border-radius: 50%;
          background: rgba(255,255,255,.15);
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: var(--serif);
          font-size: 14px;
          font-weight: 700;
        }
        .ch-name { font-size: 15px; font-weight: 700; }
        .ch-status { font-size: 10px; opacity: 0.7; }

        .chat-msgs {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          background: #f5f1ed;
          scroll-behavior: smooth;
        }
        .chat-msgs::-webkit-scrollbar { width: 4px; }
        .chat-msgs::-webkit-scrollbar-thumb { background: rgba(0,0,0,.1); border-radius: 2px; }

        .chat-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 10px;
          height: 100%;
          color: var(--text-3);
          font-size: 13px;
          text-align: center;
          padding: 32px;
        }
        .quick-prompts { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
        .quick-btn {
          background: var(--green);
          color: #fff;
          border: none;
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.15s, transform 0.15s;
          font-family: var(--sans);
        }
        .quick-btn:hover { opacity: 0.85; transform: translateY(-1px); }

        .cm {
          max-width: 82%;
          padding: 8px 12px 4px;
          border-radius: 10px;
          font-size: 13px;
          line-height: 1.5;
          white-space: pre-wrap;
          word-break: break-word;
          animation: msgIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes msgIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: none; }
        }
        .cm.user {
          background: #DCF8C6;
          align-self: flex-end;
          border-radius: 10px 0 10px 10px;
        }
        .cm.bot {
          background: #fff;
          align-self: flex-start;
          border-radius: 0 10px 10px 10px;
          border: 1px solid rgba(0,0,0,.06);
        }
        .cm-text { }
        .cm-time { font-size: 9px; color: #999; text-align: right; margin-top: 2px; }
        .cm strong { font-weight: 700; display: block; }
        .msg-brand { font-weight: 700; color: var(--text); }
        .msg-section { display: block; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--green); margin: 6px 0 2px; }
        .msg-save { display: inline-block; background: rgba(13,124,86,.08); color: var(--green); padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; margin-top: 3px; }
        .msg-store { display: block; color: var(--text-2); font-size: 12px; }

        .typing { padding: 12px 16px; }
        .typing-dots { display: flex; gap: 4px; align-items: center; }
        .typing-dots span {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: var(--text-3);
          animation: bounce 1.2s infinite;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; }
          40% { transform: scale(1.1); opacity: 1; }
        }

        .chat-input-bar {
          display: flex;
          gap: 8px;
          padding: 12px 14px;
          background: #fff;
          border-top: 1px solid var(--line);
        }
        .chat-input {
          flex: 1;
          border: 1.5px solid var(--line);
          border-radius: 24px;
          padding: 10px 16px;
          font-size: 13px;
          font-family: var(--sans);
          outline: none;
          transition: border-color 0.2s;
          background: var(--bg);
        }
        .chat-input:focus { border-color: var(--green); }
        .send-btn {
          width: 40px; height: 40px;
          border-radius: 50%;
          background: var(--green);
          color: #fff;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: opacity 0.15s, transform 0.15s;
        }
        .send-btn:hover:not(:disabled) { opacity: 0.85; transform: scale(1.05); }
        .send-btn:disabled { background: var(--text-3); cursor: not-allowed; }

        @media (max-width: 860px) {
          .demo-section .container {
            grid-template-columns: 1fr;
            gap: 40px;
          }
        }
        @media (max-width: 480px) {
          .stats { gap: 24px; }
        }
      `}</style>
    </section>
  )
}