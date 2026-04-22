export default function CTASection() {
  return (
    <section className="bottom-cta">
      <div className="container">
        <div className="cta-inner">
          <h2>
            Stop overpaying for<br />
            your <span className="green">medicines.</span>
          </h2>
          <p>Try the live demo above, or sign up to get notified when we launch on WhatsApp.</p>
          <div className="cta-btns">
            <a href="#demo" className="cta-primary">
              Try the Demo
            </a>
            <a href="#waitlist" className="cta-secondary">
              Get early access
            </a>
          </div>
          <p className="note">Free forever. No app. No signup needed for the demo.</p>
        </div>
      </div>
    </section>
  )
}
