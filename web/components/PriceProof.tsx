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
      <style>{`
        .price-proof { padding: clamp(64px, 9vh, 100px) 0; }
        .pp-inner {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 64px;
          align-items: center;
        }
        .pp-text h2 {
          font-family: var(--serif);
          font-size: clamp(28px, 3.4vw, 42px);
          font-weight: 700;
          letter-spacing: -1px;
          line-height: 1.1;
          margin-bottom: 20px;
        }
        .pp-text h2 span { color: var(--green); }
        .pp-text > p {
          font-size: 15px;
          color: var(--text-2);
          line-height: 1.7;
          margin-bottom: 28px;
          max-width: 420px;
        }
        .pp-list { display: flex; flex-direction: column; gap: 16px; }
        .pp-item { display: flex; gap: 12px; align-items: flex-start; }
        .pp-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: var(--green);
          margin-top: 6px;
          flex-shrink: 0;
        }
        .pp-item span { font-size: 14px; color: var(--text-2); line-height: 1.55; }
        .pp-item strong { color: var(--text); }
        .pp-card {
          border: 1px solid var(--line);
          border-radius: 16px;
          overflow: hidden;
          background: var(--card);
        }
        .pp-card-head {
          padding: 28px 32px;
          border-bottom: 1px solid var(--line);
        }
        .pp-card-head .label {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: var(--text-3);
          margin-bottom: 6px;
        }
        .pp-card-head .name {
          font-family: var(--serif);
          font-size: 24px;
          font-weight: 700;
          letter-spacing: -0.5px;
        }
        .pp-card-head .salt {
          font-size: 13px;
          color: var(--text-3);
          margin-top: 2px;
        }
        .pp-card-body { padding: 28px 32px; }
        .pp-prices { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }
        .pp-col { padding: 20px; border-radius: 12px; text-align: center; }
        .pp-col.br { background: rgba(196,58,49,.03); border: 1px solid rgba(196,58,49,.08); }
        .pp-col.gn { background: rgba(13,124,86,.03); border: 1px solid rgba(13,124,86,.08); }
        .pp-col .t { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px; }
        .pp-col.br .t { color: var(--red); }
        .pp-col.gn .t { color: var(--green); }
        .pp-col .a { font-family: var(--serif); font-size: 36px; font-weight: 700; letter-spacing: -0.5px; }
        .pp-col.br .a { color: var(--red); text-decoration: line-through; text-decoration-thickness: 2px; }
        .pp-col.gn .a { color: var(--green); }
        .pp-col .s { font-size: 11px; color: var(--text-3); margin-top: 2px; }
        .pp-save {
          background: var(--text);
          color: #fff;
          border-radius: 12px;
          padding: 18px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 8px;
        }
        .pp-save .l { font-size: 13px; color: rgba(255,255,255,.5); }
        .pp-save .v { font-family: var(--serif); font-size: 24px; color: var(--green-wa); letter-spacing: -0.5px; }
        @media (max-width: 860px) {
          .pp-inner { grid-template-columns: 1fr; gap: 40px; }
          .pp-prices { grid-template-columns: 1fr; }
          .pp-save { flex-direction: column; text-align: center; gap: 6px; }
        }
      `}</style>
    </section>
  )
}