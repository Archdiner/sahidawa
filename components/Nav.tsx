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
    </nav>
  )
}