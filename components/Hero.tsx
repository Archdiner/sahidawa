export default function Hero() {
  return (
    <section className="hero">
      <div className="container">
        <div className="hero-inner">
          <div className="hero-text">
            <div className="hero-kicker">Medicine price transparency</div>
            <h1>
              You're paying 3×<br />
              for the <span className="green">same medicine.</span>
            </h1>
            <p className="hero-sub">
              SahiDawa finds the identical generic alternative for any medicine in India.
              Type any name below — branded, misspelled, or generic — and see real results instantly.
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

          <div className="hero-visual">
            <div className="hero-badge">
              <span className="pct">90%</span>
              <span className="pct-label">savings</span>
            </div>
            <div className="hero-card">
              <div className="hc-label">Live example</div>
              <div className="hc-name">Augmentin 625 Duo</div>
              <div className="hc-salt">Amoxicillin 500mg + Clavulanic Acid 125mg</div>
              <div className="hc-prices">
                <div className="hc-col branded">
                  <div className="hc-col-label">What you pay</div>
                  <div className="hc-price">&#8377;228</div>
                  <div className="hc-sub">branded · strip of 10</div>
                </div>
                <div className="hc-col generic">
                  <div className="hc-col-label">Generic alternative</div>
                  <div className="hc-price">&#8377;64</div>
                  <div className="hc-sub">same salt · strip of 10</div>
                </div>
              </div>
              <div className="hc-save">
                <span className="hc-save-label">You save per strip</span>
                <span className="hc-save-val">&#8377;164 &nbsp;·&nbsp; 72%</span>
              </div>
              <div className="hc-store">
                <div className="hc-store-dot" />
                <div className="hc-store-text">
                  <strong>Jan Aushadhi store 1.8 km away</strong> — same molecule, CDSCO approved, &#8377;42/strip
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
