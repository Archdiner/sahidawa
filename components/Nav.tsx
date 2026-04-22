export default function Nav() {
  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-wrap">
          <a href="/" className="mark">
            Sahi<span className="green">Dawa</span>
          </a>
          <div className="nav-r">
            <a href="#demo" className="link hide-mobile">Live Demo</a>
            <a href="#how" className="link hide-mobile">How it works</a>
            <a href="#why" className="link hide-mobile">Why us</a>
            <a href="#waitlist" className="cta">Get early access</a>
          </div>
        </div>
      </div>
      <style>{`
        .nav {
          position: sticky;
          top: 0;
          z-index: 90;
          background: var(--bg);
          border-bottom: 1px solid var(--line);
          height: 64px;
          display: flex;
          align-items: center;
        }
        .nav-wrap {
          max-width: 1140px;
          margin: 0 auto;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 clamp(24px, 5vw, 64px);
        }
        .mark {
          font-family: var(--serif);
          font-size: 21px;
          font-weight: 700;
          letter-spacing: -0.3px;
        }
        .nav-r {
          display: flex;
          align-items: center;
          gap: 28px;
        }
        .nav-r .link {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-3);
          transition: color 0.15s;
          letter-spacing: 0.01em;
        }
        .nav-r .link:hover { color: var(--text); }
        .nav-r .cta {
          font-size: 13px;
          font-weight: 700;
          color: #fff;
          background: var(--green);
          padding: 9px 20px;
          border-radius: 8px;
          transition: opacity 0.15s;
        }
        .nav-r .cta:hover { opacity: 0.85; }
        @media (max-width: 600px) {
          .nav-r .link { display: none; }
        }
      `}</style>
    </nav>
  )
}