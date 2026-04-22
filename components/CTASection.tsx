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
      <style>{`
        .bottom-cta {
          padding: clamp(64px, 9vh, 100px) 0;
          text-align: center;
        }
        .cta-inner { max-width: 600px; margin: 0 auto; }
        .bottom-cta h2 {
          font-family: var(--serif);
          font-size: clamp(32px, 4.2vw, 52px);
          font-weight: 700;
          letter-spacing: -1.5px;
          line-height: 1.05;
          margin-bottom: 16px;
        }
        .bottom-cta .cta-inner > p {
          font-size: 16px;
          color: var(--text-2);
          margin-bottom: 36px;
          line-height: 1.6;
        }
        .cta-btns {
          display: flex;
          gap: 12px;
          justify-content: center;
          flex-wrap: wrap;
        }
        .cta-primary {
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
        .cta-primary:hover {
          background: var(--green);
          transform: translateY(-1px);
        }
        .cta-secondary {
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
        .cta-secondary:hover {
          border-color: var(--green);
          color: var(--green);
        }
        .bottom-cta .note {
          font-size: 12px;
          color: var(--text-3);
          margin-top: 16px;
          margin-bottom: 0;
        }
      `}</style>
    </section>
  )
}
