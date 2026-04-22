export default function Footer() {
  return (
    <footer className="foot">
      <div className="foot-top">
        <div className="container">
          <div className="foot-inner">
            <div className="foot-left">
              <div className="mark">Sahi<span className="green">Dawa</span></div>
              <p>
                India's first medicine price discovery platform.<br />
                Built entirely on the patient's side.
              </p>
            </div>
            <div className="foot-cols">
              <div className="foot-col">
                <h6>Data Sources</h6>
                <a href="#">PMBJP Store List</a>
                <a href="#">NPPA Price Ceilings</a>
                <a href="#">CDSCO Drug Index</a>
              </div>
              <div className="foot-col">
                <h6>Legal</h6>
                <a href="#">Privacy</a>
                <a href="#">Disclaimer</a>
                <a href="#">Contact</a>
              </div>
            </div>
          </div>
          <div className="foot-bottom">
            <p>&copy; 2026 SahiDawa</p>
            <p className="foot-disclaimer">
              SahiDawa provides pricing information only. We do not sell, prescribe,
              or recommend medicines. Always consult your doctor before switching.
              Prices are indicative.
            </p>
          </div>
        </div>
      </div>
      <style>{`
        .foot {
          border-top: 1px solid var(--line);
          padding: 48px 0 32px;
        }
        .foot-top { }
        .foot-inner {
          display: flex;
          justify-content: space-between;
          align-items: start;
          flex-wrap: wrap;
          gap: 32px;
          margin-bottom: 28px;
        }
        .foot-left { max-width: 300px; }
        .foot-left .mark {
          font-family: var(--serif);
          font-size: 21px;
          font-weight: 700;
          margin-bottom: 12px;
        }
        .foot-left p {
          font-size: 13px;
          color: var(--text-3);
          line-height: 1.65;
        }
        .foot-cols { display: flex; gap: 48px; }
        .foot-col h6 {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: var(--text-3);
          margin-bottom: 14px;
        }
        .foot-col a {
          display: block;
          font-size: 13px;
          color: var(--text-3);
          margin-bottom: 8px;
          transition: color 0.15s;
        }
        .foot-col a:hover { color: var(--green); }
        .foot-bottom {
          display: flex;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 12px;
          padding-top: 20px;
          border-top: 1px solid var(--line);
        }
        .foot-bottom > p {
          font-size: 11px;
          color: var(--text-3);
        }
        .foot-disclaimer {
          font-size: 10px !important;
          color: var(--text-3) !important;
          max-width: 480px;
          line-height: 1.5;
          opacity: 0.7;
        }
        @media (max-width: 860px) {
          .foot-inner { flex-direction: column; }
        }
      `}</style>
    </footer>
  )
}