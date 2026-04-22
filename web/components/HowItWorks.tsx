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
      <style>{`
        .how { padding: clamp(64px, 9vh, 100px) 0; }
        .how-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 40px;
          margin-bottom: 56px;
          flex-wrap: wrap;
        }
        .how-top h2 {
          font-family: var(--serif);
          font-size: clamp(28px, 3.4vw, 42px);
          font-weight: 700;
          letter-spacing: -1px;
          line-height: 1.1;
          max-width: 400px;
        }
        .how-top p {
          font-size: 14px;
          color: var(--text-3);
          max-width: 340px;
          line-height: 1.65;
          text-align: right;
        }
        .how-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1px;
          background: var(--line);
          border: 1px solid var(--line);
          border-radius: 16px;
          overflow: hidden;
        }
        .how-cell {
          background: var(--card);
          padding: 40px 32px;
        }
        .how-cell .num {
          font-family: var(--serif);
          font-size: 36px;
          font-weight: 700;
          color: var(--green);
          margin-bottom: 20px;
          letter-spacing: -1px;
        }
        .how-cell h3 {
          font-size: 17px;
          font-weight: 700;
          margin-bottom: 10px;
          letter-spacing: -0.2px;
        }
        .how-cell p {
          font-size: 13.5px;
          color: var(--text-2);
          line-height: 1.65;
        }
        @media (max-width: 860px) {
          .how-row { grid-template-columns: 1fr; }
          .how-top p { text-align: left; }
        }
      `}</style>
    </section>
  )
}