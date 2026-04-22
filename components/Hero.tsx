export default function Hero() {
  return (
    <section className="hero">
      <div className="container">
        <div className="hero-inner">
          <div className="hero-text">
            <div className="hero-kicker">Medicine price transparency · India</div>
            <h1>
              You're paying 3×<br />
              for the <span className="green">same medicine.</span>
            </h1>
            <p className="hero-sub">
              Type any medicine name below and instantly see the cheapest generic alternative,
              government ceiling price, and the nearest Jan Aushadhi store.
            </p>
            <div className="hero-btns">
              <a href="#demo" className="primary">
                Try it now — it's live
              </a>
              <a href="#waitlist" className="secondary">Get early access</a>
            </div>
            <div className="hero-stats">
              <div className="hero-stat">
                <span className="hs-num">62,000+</span>
                <span className="hs-label">Medicines mapped</span>
              </div>
              <div className="hero-stat-div" />
              <div className="hero-stat">
                <span className="hs-num">10,000+</span>
                <span className="hs-label">Jan Aushadhi stores</span>
              </div>
              <div className="hero-stat-div" />
              <div className="hero-stat">
                <span className="hs-num">Up to 90%</span>
                <span className="hs-label">Price savings</span>
              </div>
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-badge">
              <span className="pct">90%</span>
              <span className="pct-label">savings</span>
            </div>
            <div className="hero-card">
              <div className="hc-label">Real example · Diabetes medication</div>
              <div className="hc-name">Glycomet 500</div>
              <div className="hc-salt">Metformin Hydrochloride 500mg · 15 tablets</div>
              <div className="hc-prices">
                <div className="hc-col branded">
                  <div className="hc-col-label">Branded</div>
                  <div className="hc-price">&#8377;42</div>
                  <div className="hc-sub">what you pay today</div>
                </div>
                <div className="hc-col generic">
                  <div className="hc-col-label">Generic</div>
                  <div className="hc-price">&#8377;9</div>
                  <div className="hc-sub">same salt, same dose</div>
                </div>
              </div>
              <div className="hc-save">
                <span className="hc-save-label">You save every month</span>
                <span className="hc-save-val">&#8377;33 · 79%</span>
              </div>
              <div className="hc-store">
                <div className="hc-store-dot" />
                <div className="hc-store-text">
                  <strong>Jan Aushadhi store nearby</strong> — CDSCO approved · &#8377;6/strip
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
