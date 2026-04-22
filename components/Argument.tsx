'use client'
import { useEffect, useRef, useState } from 'react'

const CARDS = [
  {
    tag: 'Online pharmacies',
    title: '1mg and PharmEasy earn more when you buy branded',
    body: 'They make revenue on medicine sales. Showing you a generic at a store nearby destroys their margins. They will never build this.',
  },
  {
    tag: 'Retail chains',
    title: 'Apollo and MedPlus profit from the price gap',
    body: '10,000+ stores earning more on branded medicines. Every commercial incentive points toward keeping you uninformed.',
  },
  {
    tag: 'The gap we fill',
    title: 'The government built 10,000 generic stores. Nobody built the way to find them.',
    body: 'Jan Aushadhi stores sell medicines at 50–90% below branded prices. But there is no search, no app, no consumer discovery layer. SahiDawa is that layer.',
    wide: true,
  },
]

export default function Argument() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  return (
    <section className="argument" id="why" ref={ref}>
      <div className="container">
        <div className={`arg-head sr ${visible ? 'v' : ''}`}>
          <h2>
            Everyone who could build this<br />
            profits from not building it.
          </h2>
          <p>
            This is not a technology problem. It's an incentive problem.
            Every existing player earns more when you stay uninformed.
          </p>
        </div>
        <div className="arg-grid">
          {CARDS.map((card, i) => (
            <div
              key={i}
              className={`arg-card sr ${card.wide ? 'wide' : ''} ${visible ? 'v' : ''}`}
              style={{ transitionDelay: `${0.1 + i * 0.1}s` }}
            >
              <div className="tag">{card.tag}</div>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </div>
          ))}
        </div>
      </div>
      <style>{`
        .argument { padding: clamp(64px, 9vh, 100px) 0; }
        .arg-head { margin-bottom: 56px; }
        .arg-head h2 {
          font-family: var(--serif);
          font-size: clamp(28px, 3.4vw, 42px);
          font-weight: 700;
          letter-spacing: -1px;
          line-height: 1.1;
          margin-bottom: 16px;
        }
        .arg-head p {
          font-size: 15px;
          color: var(--text-2);
          line-height: 1.65;
          max-width: 560px;
        }
        .arg-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        .arg-card {
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 36px 32px;
          background: var(--card);
          transition: border-color 0.3s;
        }
        .arg-card:hover { border-color: var(--green); }
        .arg-card.wide {
          grid-column: 1 / -1;
          background: var(--text);
          color: #fff;
          border-color: transparent;
        }
        .arg-card .tag {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: var(--green);
          margin-bottom: 14px;
        }
        .arg-card.wide .tag { color: rgba(255,255,255,0.4); }
        .arg-card h3 {
          font-size: 18px;
          font-weight: 700;
          margin-bottom: 10px;
          letter-spacing: -0.2px;
          line-height: 1.3;
        }
        .arg-card p {
          font-size: 13.5px;
          color: var(--text-2);
          line-height: 1.65;
        }
        .arg-card.wide p { color: rgba(255,255,255,0.5); }
        .arg-card.wide:hover { border-color: var(--green); }
        @media (max-width: 860px) {
          .arg-grid { grid-template-columns: 1fr; }
          .arg-card.wide { grid-column: 1; }
        }
      `}</style>
    </section>
  )
}