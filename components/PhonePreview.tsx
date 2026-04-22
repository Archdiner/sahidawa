'use client'
import { useEffect, useRef, useState } from 'react'

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
  time: string
}

const SAMPLE_MESSAGES: Message[] = [
  { id: 1, sender: 'user', text: 'Augmentin 625', time: '10:32 AM' },
  {
    id: 2,
    sender: 'bot',
    time: '10:32 AM',
    text: `[BRAND] Augmentin 625 Duo Tablet
Salt: Amoxicillin 500mg + Clavulanic Acid 125mg
MRP: Rs.223.42 (strip of 10 tablets)
By: GlaxoSmithKline

[CHEAPEST GENERIC]
Amoxyclav 625 Tablet
Price: Rs.64.00 (strip of 10 tablets)
By: Mankind Pharma
You save: Rs.159.42 (71%)

[GOVT CEILING PRICE]: Rs.22.85/unit

[JAN AUSHADHI STORES NEAR YOU]:
  1. Jan Aushadhi Store PMBJK00863
     Mm-1/70 Sector- A, Sbi Colony, Lucknow
     1.8 km away
     Phone: 9415107229

[WARNING] Always consult your doctor before switching medicines.`,
  },
  { id: 3, sender: 'user', text: 'Show on map', time: '10:33 AM' },
]

export default function PhonePreview() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [show, setShow] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  // Animate messages one by one when visible
  useEffect(() => {
    if (!visible) return
    const timeouts: ReturnType<typeof setTimeout>[] = []

    SAMPLE_MESSAGES.forEach((msg, i) => {
      const t = setTimeout(() => {
        setMessages(prev => [...prev, msg])
      }, 1200 + i * 2000)
      timeouts.push(t)
    })

    return () => timeouts.forEach(clearTimeout)
  }, [visible])

  return (
    <div ref={ref} className={`phone-wrap sr ${visible ? 'v' : ''}`}>
      <div className="phone">
        <div className="phone-inner">
          <div className="ph-bar">
            <div className="ph-ava">S</div>
            <div>
              <div className="ph-name">SahiDawa</div>
              <div className="ph-status">online</div>
            </div>
          </div>
          <div className="ph-msgs">
            {messages.map(m => (
              <div key={m.id} className={`m ${m.sender}`}>
                {m.text.split('\n').map((line, i) => {
                  if (line.startsWith('[BRAND]')) return <strong key={i}>{line}</strong>
                  if (line.startsWith('[CHEAPEST GENERIC]') || line.startsWith('[JAN') || line.startsWith('[WARNING]') || line.startsWith('[GOVT')) {
                    return <span key={i} className="tag">{line}</span>
                  }
                  if (line.startsWith('Save')) {
                    return <span key={i} className="sv">{line}</span>
                  }
                  // strikethrough price
                  const mrp = line.match(/(Rs\.?\s*[\d.]+)/)
                  return (
                    <span key={i}>
                      {line}
                      {i === 0 && mrp && <span className="strike"> {line.match(/Rs\.?\s*[\d.]+/)?.[0]}</span>}
                    </span>
                  )
                })}
                <div className="ts">{m.time}</div>
              </div>
            ))}
            {messages.length === 0 && (
              <div className="m in" style={{ alignSelf: 'flex-start', opacity: 0.5, fontSize: '12px' }}>
                Type a medicine name to begin...
              </div>
            )}
          </div>
        </div>
      </div>
      <style>{`
        .phone-wrap {
          display: flex;
          justify-content: center;
        }
        .phone {
          background: #000;
          border-radius: 32px;
          padding: 8px;
          box-shadow: 0 32px 64px rgba(0,0,0,.12);
          max-width: 380px;
          width: 100%;
        }
        .phone-inner {
          background: #ece5dd;
          border-radius: 24px;
          overflow: hidden;
        }
        .ph-bar {
          background: #075E54;
          padding: 12px 14px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #fff;
        }
        .ph-ava {
          width: 30px;
          height: 30px;
          border-radius: 50%;
          background: rgba(255,255,255,.12);
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: var(--serif);
          font-size: 13px;
          font-weight: 600;
        }
        .ph-name { font-size: 14px; font-weight: 700; }
        .ph-status { font-size: 10px; opacity: 0.7; }
        .ph-msgs {
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          min-height: 380px;
        }
        .m {
          max-width: 88%;
          padding: 8px 11px 4px;
          border-radius: 7px;
          font-size: 12.5px;
          line-height: 1.5;
          white-space: pre-wrap;
          word-break: break-word;
          animation: msgIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes msgIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: none; }
        }
        .m.out {
          background: #DCF8C6;
          align-self: flex-end;
          border-radius: 7px 0 7px 7px;
        }
        .m.in {
          background: #fff;
          align-self: flex-start;
          border-radius: 0 7px 7px 7px;
        }
        .m strong { font-weight: 700; display: block; margin-bottom: 2px; }
        .m .tag { display: block; color: var(--green); font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; margin: 4px 0 2px; }
        .m .sv { display: inline-block; background: rgba(13,124,86,.08); color: var(--green); padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; margin-top: 3px; }
        .m .strike { text-decoration: line-through; color: var(--red); }
        .m .ts { font-size: 9px; color: #999; text-align: right; margin-top: 2px; }
      `}</style>
    </div>
  )
}