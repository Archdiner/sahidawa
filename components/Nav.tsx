export default function Nav() {
  return (
    <nav className="nav">
      <div className="nav-wrap">
        <a href="/" className="mark">
          Sahi<span className="green">Dawa</span>
        </a>
        <div className="nav-r">
          <a href="#demo" className="link">Live Demo</a>
          <a href="#how" className="link">How it works</a>
          <a href="#why" className="link">Why us</a>
          <a href="#waitlist" className="cta">Get early access</a>
        </div>
      </div>
    </nav>
  )
}