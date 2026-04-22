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
    </footer>
  )
}