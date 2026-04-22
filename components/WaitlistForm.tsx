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
      if (!res.ok) {
        setErrorMsg(data.error || 'Something went wrong.')
        setStatus('error')
      } else {
        setStatus('success')
      }
    } catch {
      setErrorMsg('Network error. Please try again.')
      setStatus('error')
    }
  }

  return (
    <section className="waitlist" id="waitlist" ref={ref}>
      <div className="container">
        <div className={`wl-inner sr ${visible ? 'v' : ''}`}>
          <h2>
            Be the first to<br />
            <span>stop overpaying.</span>
          </h2>
          <p className="wl-sub">
            We're launching SahiDawa on WhatsApp soon. Sign up to get early access
            — and start saving from day one.
          </p>

          {status === 'success' ? (
            <div className="wl-success">
              <div className="wl-check">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="28" height="28">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p className="wl-done-title">You're on the list!</p>
              <p className="wl-done-sub">We'll notify you as soon as SahiDawa goes live on WhatsApp.</p>
            </div>
          ) : (
            <form className="wl-form" onSubmit={handleSubmit}>
              <div className="wl-fields">
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
                  placeholder="Your email address"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                className="wl-btn"
                disabled={status === 'loading' || !email.trim()}
              >
                {status === 'loading' ? 'Joining...' : 'Get early access'}
              </button>
              {status === 'error' && <p className="wl-error">{errorMsg}</p>}
              <p className="wl-note">Free forever. No spam. Unsubscribe anytime.</p>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}
