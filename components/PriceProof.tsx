'use client'
import { useEffect, useRef, useState } from 'react'

export default function PriceProof() {
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
    <section className="price-proof" ref={ref}>
      <div className="container">
        <div className={`pp-inner sr ${visible ? 'v' : ''}`}>
          <div className="pp-text">
            <h2>
              Same molecule.<br />
              Same cure.<br />
              <span>70% less.</span>
            </h2>
            <p>
              Every generic in India contains the identical active ingredient
              as the branded version. The difference is the label and the bill.
            </p>
            <div className="pp-list">
              {[
                {
                  title: 'Identical salt composition',
                  body: 'Same molecule, same dosage, same bioequivalence',
                },
                {
                  title: 'CDSCO approved',
                  body: 'Passes the same regulatory quality standards',
                },
                {
                  title: 'Used in every government hospital',
                  body: 'Doctors trust generics for their own patients',
                },
              ].map(item => (
                <div key={item.title} className="pp-item">
                  <div className="pp-dot" />
                  <span>
                    <strong>{item.title}</strong> — {item.body}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="pp-card">
            <div className="pp-card-head">
              <div className="label">Real example</div>
              <div className="name">Augmentin 625 Duo</div>
              <div className="salt">Amoxicillin 500mg + Clavulanic Acid 125mg</div>
            </div>
            <div className="pp-card-body">
              <div className="pp-prices">
                <div className="pp-col br">
                  <div className="t">Branded</div>
                  <div className="a">&#8377;228</div>
                  <div className="s">per strip of 10</div>
                </div>
                <div className="pp-col gn">
                  <div className="t">Generic</div>
                  <div className="a">&#8377;68</div>
                  <div className="s">per strip of 10</div>
                </div>
              </div>
              <div className="pp-save">
                <div className="l">You save per strip</div>
                <div className="v">&#8377;160 (70%)</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}