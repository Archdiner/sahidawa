export default function Hero() {
  return (
    <section className="hero">
      <div className="container">
        <div className="hero-kicker">Medicine price transparency</div>
        <h1>
          You pay &#8377;223 for a medicine<br />
          that costs <span className="green">&#8377;64.</span>
        </h1>
        <p className="hero-sub">
          SahiDawa finds the identical generic alternative for any medicine in India
          and tells you where to buy it near you. Try it live below — type any medicine name and see real results.
        </p>
        <div className="hero-btns">
          <a href="#demo" className="primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Try it now — it's live
          </a>
          <a href="#waitlist" className="secondary">Get early access</a>
        </div>
      </div>
      <style>{`
        .hero {
          padding: clamp(72px, 10vh, 120px) clamp(24px, 5vw, 64px) 0;
          max-width: 1140px;
          margin: 0 auto;
        }
        .hero-kicker {
          font-size: 13px;
          font-weight: 700;
          color: var(--green);
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-bottom: 20px;
        }
        .hero h1 {
          font-family: var(--serif);
          font-size: clamp(40px, 5.6vw, 72px);
          font-weight: 700;
          line-height: 1;
          letter-spacing: -2.5px;
          margin-bottom: 28px;
        }
        .hero-sub {
          font-size: clamp(16px, 1.6vw, 19px);
          line-height: 1.65;
          color: var(--text-2);
          max-width: 540px;
          margin-bottom: 40px;
        }
        .hero-btns {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          margin-bottom: clamp(64px, 9vh, 100px);
        }
        .hero-btns .primary {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: var(--text);
          color: #fff;
          padding: 15px 28px;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 700;
          transition: background 0.2s, transform 0.15s;
        }
        .hero-btns .primary:hover {
          background: var(--green);
          transform: translateY(-1px);
        }
        .hero-btns .secondary {
          display: inline-flex;
          align-items: center;
          padding: 15px 24px;
          border: 1.5px solid var(--line);
          border-radius: 10px;
          font-size: 14px;
          font-weight: 600;
          color: var(--text-2);
          transition: border-color 0.2s, color 0.2s;
        }
        .hero-btns .secondary:hover {
          border-color: var(--green);
          color: var(--green);
        }
      `}</style>
    </section>
  )
}