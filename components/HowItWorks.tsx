'use client'
import { useEffect, useRef, useState } from 'react'

const STEPS = [
  {
    num: '01',
    title: 'Type any medicine name',
    body: 'Branded, generic, or misspelled — Crocin, paracetomol, Glycomet. Our system understands all of them.',
  },
  {
    num: '02',
    title: 'Get the cheapest alternative',
    body: 'Instantly see the generic equivalent, the government ceiling price, and the nearest Jan Aushadhi store.',
  },
  {
    num: '03',
    title: 'Walk in and save',
    body: 'Same molecule. Same CDSCO approval. Same efficacy. A fraction of the price.',
  },
]

export default function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  return (
    <section className="how" id="how" ref={ref}>
      <div className="container">
        <div className={`how-head sr ${visible ? 'v' : ''}`}>
          <p className="how-eyebrow">How it works</p>
          <h2>Three steps.<br />Three seconds.</h2>
        </div>
        <div className={`how-steps sr ${visible ? 'v' : ''}`} style={{ transitionDelay: '0.1s' }}>
          {STEPS.map((step, i) => (
            <div key={step.num} className="how-step">
              <div className="how-step-num">{step.num}</div>
              <div className="how-step-body">
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
              {i < STEPS.length - 1 && <div className="how-step-arrow">→</div>}
            </div>
          ))}
        </div>
        <p className={`how-foot sr ${visible ? 'v' : ''}`} style={{ transitionDelay: '0.2s' }}>
          No app. No account. No download.
        </p>
      </div>
    </section>
  )
}
