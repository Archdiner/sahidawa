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
      <style>{`
        .waitlist {
          padding: clamp(64px, 9vh, 100px) 0;
          text-align: center;
        }
        .wl-inner {
          max-width: 520px;
          margin: 0 auto;
        }
        .waitlist h2 {
          font-family: var(--serif);
          font-size: clamp(32px, 4.2vw, 52px);
          font-weight: 700;
          letter-spacing: -1.5px;
          line-height: 1.05;
          margin-bottom: 16px;
        }
        .waitlist h2 span { color: var(--green); }
        .wl-sub {
          font-size: 16px;
          color: var(--text-2);
          line-height: 1.6;
          margin-bottom: 36px;
        }

        .wl-form {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }
        .wl-fields {
          display: flex;
          gap: 10px;
          width: 100%;
        }
        .wl-input {
          flex: 1;
          padding: 14px 18px;
          border: 1.5px solid var(--line);
          border-radius: 10px;
          font-size: 14px;
          font-family: var(--sans);
          background: var(--card);
          outline: none;
          transition: border-color 0.2s;
        }
        .wl-input:focus { border-color: var(--green); }
        .wl-btn {
          width: 100%;
          padding: 16px 32px;
          background: var(--text);
          color: #fff;
          border: none;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 700;
          font-family: var(--sans);
          cursor: pointer;
          transition: background 0.2s, transform 0.15s;
        }
        .wl-btn:hover:not(:disabled) {
          background: var(--green);
          transform: translateY(-1px);
        }
        .wl-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .wl-note {
          font-size: 12px;
          color: var(--text-3);
          margin-top: 4px;
        }
        .wl-error {
          font-size: 13px;
          color: var(--red);
        }

        .wl-success {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 32px;
        }
        .wl-check {
          width: 56px; height: 56px;
          border-radius: 50%;
          background: rgba(13,124,86,.08);
          color: var(--green);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 8px;
        }
        .wl-done-title {
          font-family: var(--serif);
          font-size: 24px;
          font-weight: 700;
        }
        .wl-done-sub {
          font-size: 14px;
          color: var(--text-3);
        }

        @media (max-width: 480px) {
          .wl-fields { flex-direction: column; }
        }
      `}</style>
    </section>
  )
}
