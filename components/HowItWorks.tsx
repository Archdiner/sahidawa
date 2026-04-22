'use client'
import { useEffect, useRef, useState } from 'react'

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
        <div className={`how-top sr ${visible ? 'v' : ''}`}>
          <h2>
            One message.<br />
            Three answers.<br />
            Three seconds.
          </h2>
          <p>
            No app to download. No account to create.<br />
            Try the live demo above — or wait for our WhatsApp launch.
          </p>
        </div>
        <div className={`how-row sr ${visible ? 'v' : ''}`} style={{ transitionDelay: '0.15s' }}>
          {[
            {
              num: '01',
              title: 'Send any medicine name',
              body: 'Branded, generic, misspelled — our system understands all of them. Just type and send.',
            },
            {
              num: '02',
              title: 'Get the real alternatives',
              body: 'See the cheapest generic equivalent, the nearest Jan Aushadhi government store, and local chemist discounts.',
            },
            {
              num: '03',
              title: 'Walk in and save',
              body: 'Same active ingredient. Same CDSCO approval. Same efficacy. Different price tag — up to 90% less.',
            },
          ].map(cell => (
            <div key={cell.num} className="how-cell">
              <div className="num">{cell.num}</div>
              <h3>{cell.title}</h3>
              <p>{cell.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}