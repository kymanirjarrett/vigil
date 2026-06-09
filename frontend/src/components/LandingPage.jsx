import { Link } from "react-router-dom";

const FEATURES = [
  {
    icon: "◈",
    title: "Real-time monitoring",
    desc: "Live visibility into every AWS Glue job run — status, duration, and DPU consumption at a glance.",
  },
  {
    icon: "⚑",
    title: "Anomaly detection",
    desc: "Z-score analysis flags jobs running outside historical norms before they become incidents.",
  },
  {
    icon: "⊛",
    title: "Smart alerting",
    desc: "Threshold-based alerts on duration and DPU. Trigger manually or let the engine catch anomalies.",
  },
  {
    icon: "⊕",
    title: "RBAC + Audit logging",
    desc: "Admin and analyst roles with immutable, append-only audit trails. Every action recorded.",
  },
  {
    icon: "⊗",
    title: "Multi-cloud",
    desc: "Azure Data Factory and GCP Dataflow support.",
    comingSoon: true,
  },
  {
    icon: "⊙",
    title: "Security event monitoring",
    desc: "Complete auth event stream with credential-stuffing detection.",
    comingSoon: true,
  },
];

const STEPS = [
  {
    n: "01",
    title: "Connect AWS",
    desc: "Provide your AWS credentials and Glue region. Vigil connects directly to the AWS Glue Jobs API.",
  },
  {
    n: "02",
    title: "Vigil monitors",
    desc: "Historical run data is analyzed. Anomalies are detected. Your entire pipeline is visible in one view.",
  },
  {
    n: "03",
    title: "Get alerted",
    desc: "When something breaks pattern, you know immediately — not after a 4-hour debugging session.",
  },
];

export default function LandingPage() {
  return (
    <div className="landing">
      {/* ── Nav ── */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">VIGIL</span>
        </div>
        <div className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
        </div>
        <div className="landing-nav-actions">
          <Link to="/login" className="landing-btn-ghost">Log in</Link>
          <Link to="/signup" className="landing-btn-primary">Sign up</Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-eyebrow">
            <span className="pulse" />
            <span>AWS Glue ETL observability</span>
          </div>
          <h1 className="landing-headline">
            Catch pipeline problems<br />
            before your users do.
          </h1>
          <p className="landing-subhead">
            Vigil gives AWS Glue teams real-time visibility, anomaly detection,
            and instant alerting — built for the ops engineers who own the pipeline.
          </p>
          <div className="landing-ctas">
            <Link to="/signup" className="landing-btn-primary landing-btn-lg">
              Get started →
            </Link>
            <Link to="/signup" className="landing-btn-ghost landing-btn-lg">
              View demo
            </Link>
          </div>
          <p className="landing-cta-hint">Free to use · No credit card required</p>
        </div>

        {/* Terminal-style preview card */}
        <div className="landing-terminal">
          <div className="landing-terminal-header">
            <span className="landing-terminal-dot" style={{ background: "var(--danger)" }} />
            <span className="landing-terminal-dot" style={{ background: "var(--warn)" }} />
            <span className="landing-terminal-dot" style={{ background: "var(--accent)" }} />
            <span className="landing-terminal-title">vigil — job monitor</span>
          </div>
          <div className="landing-terminal-body">
            {[
              { job: "customer_ingest_daily",   status: "SUCCEEDED", dur: "14m 02s", dpu: "10", ok: true  },
              { job: "product_sync_hourly",      status: "RUNNING",   dur: "08m 41s", dpu: "10", ok: null  },
              { job: "fraud_detection_model",    status: "FAILED",    dur: "02m 11s", dpu: "10", ok: false },
              { job: "analytics_aggregation",    status: "SUCCEEDED", dur: "31m 58s", dpu: "20", ok: true  },
            ].map(row => (
              <div key={row.job} className="landing-terminal-row">
                <span className={`landing-terminal-status ${row.ok === true ? "ok" : row.ok === false ? "err" : "run"}`}>
                  {row.status}
                </span>
                <span className="landing-terminal-job">{row.job}</span>
                <span className="landing-terminal-meta">{row.dur} · {row.dpu} DPU</span>
              </div>
            ))}
            <div className="landing-terminal-anomaly">
              ⚑ anomaly — fraud_detection_model ran 3.8 σ below normal
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="landing-features" id="features">
        <div className="landing-section-label">Features</div>
        <h2 className="landing-section-title">Everything your pipeline team needs</h2>
        <div className="landing-features-grid">
          {FEATURES.map(f => (
            <div key={f.title} className={`landing-feature-card${f.comingSoon ? " landing-feature-soon" : ""}`}>
              <span className="landing-feature-icon">{f.icon}</span>
              <div>
                <div className="landing-feature-title">
                  {f.title}
                  {f.comingSoon && <span className="landing-soon-badge">coming soon</span>}
                </div>
                <p className="landing-feature-desc">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="landing-how" id="how-it-works">
        <div className="landing-section-label">How it works</div>
        <h2 className="landing-section-title">Up and running in minutes</h2>
        <div className="landing-steps">
          {STEPS.map((s, i) => (
            <div key={s.n} className="landing-step">
              <div className="landing-step-n">{s.n}</div>
              {i < STEPS.length - 1 && <div className="landing-step-connector" />}
              <div className="landing-step-title">{s.title}</div>
              <p className="landing-step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA band ── */}
      <section className="landing-cta-band">
        <h2 className="landing-cta-band-title">Ready to see your pipeline clearly?</h2>
        <Link to="/signup" className="landing-btn-primary landing-btn-lg">
          Create free account →
        </Link>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <div className="landing-footer-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">VIGIL</span>
          <span className="landing-footer-tagline">ETL Observability Platform</span>
        </div>
        <div className="landing-footer-links">
          <a
            href="https://github.com/kymanirjarrett/vigil"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <Link to="/login">Log in</Link>
          <Link to="/signup">Sign up</Link>
        </div>
        <p className="landing-footer-copy">
          © {new Date().getFullYear()} Vigil. Built by Kymani Jarrett.
        </p>
      </footer>
    </div>
  );
}
