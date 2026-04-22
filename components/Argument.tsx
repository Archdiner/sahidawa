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
    </section>
  )
}