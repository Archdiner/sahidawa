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
    </div>
  )
}