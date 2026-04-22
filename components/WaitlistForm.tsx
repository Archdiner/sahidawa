'use client'
import { useEffect, useRef, useState } from 'react'

export default function WaitlistForm() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setStatus('loading')
    setErrorMsg('')
    try {
      const res = await fetch('/_/backend/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), name: name.trim() }),
      })
      const data = await res.json()
      if (!res.ok) { setErrorMsg(data.error || 'Something went wrong.'); setStatus('error') }
      else setStatus('success')
    } catch {
      setErrorMsg('Network error. Please try again.')
      setStatus('error')
    }
  }

  return (
    <section className="waitlist" id="waitlist" ref={ref}>
      <div className="container">
        <div className={`wl-layout sr ${visible ? 'v' : ''}`}>
          <div className="wl-left">
            <p className="wl-eyebrow">Coming to WhatsApp</p>
            <h2>Stop overpaying.<br />Starting now.</h2>
            <p className="wl-pitch">
              The demo is live. WhatsApp is launching soon.
              Be the first to know — and start saving from day one.
            </p>
            <div className="wl-proof">
              <div className="wl-proof-item">
                <span className="wlp-num">&#8377;164</span>
                <span className="wlp-label">saved per antibiotic strip</span>
              </div>
              <div className="wl-proof-item">
                <span className="wlp-num">79%</span>
                <span className="wlp-label">cheaper on diabetes drugs</span>
              </div>
            </div>
          </div>

          <div className="wl-right">
            {status === 'success' ? (
              <div className="wl-success">
                <div className="wl-check">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="28" height="28">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <p className="wl-done-title">You're on the list.</p>
                <p className="wl-done-sub">We'll message you the moment SahiDawa goes live on WhatsApp.</p>
              </div>
            ) : (
              <form className="wl-form" onSubmit={handleSubmit}>
                <p className="wl-form-label">Get notified at launch</p>
                <input
                  type="text"
                  className="wl-input"
                  placeholder="Your name (optional)"
                  value={name}
                  onChange={e => setName(e.target.value)}
                />
                <input
                  type="email"
                  className="wl-input"
                  placeholder="Email address"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
                <button type="submit" className="wl-btn" disabled={status === 'loading' || !email.trim()}>
                  {status === 'loading' ? 'Joining...' : 'Get early access →'}
                </button>
                {status === 'error' && <p className="wl-error">{errorMsg}</p>}
                <p className="wl-note">Free forever · No spam · Unsubscribe anytime</p>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
