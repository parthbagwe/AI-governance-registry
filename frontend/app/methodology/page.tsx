import type { Metadata } from "next";
import {
  Database,
  ExternalLink,
  FlaskConical,
  LineChart,
  Scale,
  ShieldCheck,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Data & methodology",
  description: "Data provenance, calculations, forecast method, and regulatory sources for the AI Model Governance Registry.",
};

const DATA_SOURCES = [
  {
    name: "Twelve Data intraday FX",
    classification: "Live external data",
    models: "fx-intraday-monitor",
    detail: "One-minute USD/INR open, high, low, close, and volume bars are requested at monitoring time. The API key remains server-side. Each run records the exact window and number of newly observed bars.",
    processing: "Timestamps are sorted and deduplicated; price and range features are derived from OHLC bars. Training and monitoring windows remain separate.",
    link: "https://twelvedata.com/docs",
  },
  {
    name: "ECB reference rates via Frankfurter",
    classification: "Live and historical public data",
    models: "fx-exposure-monitor versions",
    detail: "Daily European Central Bank reference rates are retrieved through the open Frankfurter API. The repository does not fabricate or perturb these market values.",
    processing: "Currencies are expressed against INR, aligned by business date, and converted into return, volatility, range, and anomaly features.",
    link: "https://frankfurter.dev/",
  },
  {
    name: "Give Me Some Credit",
    classification: "Real static public benchmark",
    models: "personal-loan-credit-scorer",
    detail: "The anonymised 2011 Kaggle competition training file contains roughly 150,000 borrower rows and a serious-delinquency target. Kaggle withholds labels for the test file, so only labelled training rows support evaluation.",
    processing: "Known impossible age values are clipped, missing income and dependant counts are median-imputed, and the split preserves class imbalance before XGBoost evaluation.",
    link: "https://www.kaggle.com/c/GiveMeSomeCredit",
  },
  {
    name: "Synthetic SME credit data",
    classification: "Generated demonstration data",
    models: "sme-credit-scorer",
    detail: "No public dataset combines identifiable GST filings and bank transactions for Indian SMEs. The repository therefore generates fictional rows with documented correlations instead of presenting invented customer records as real.",
    processing: "Filing delay, turnover, balance, volatility, and bounce behaviour influence a synthetic default label. The data is suitable for software demonstration, not empirical credit conclusions.",
    link: null,
  },
  {
    name: "Extended model portfolio",
    classification: "Synthetic registry scenarios",
    models: "21 metadata/sample entries",
    detail: "Banking, securities, insurance, identity, cyber, payments, language-model, and compliance scenarios are seeded to exercise governance workflows. Their owners, scores, lineage, and events describe fictional teams and systems.",
    processing: "Each model receives model-specific synthetic metrics plus a clearly named demo_governance_health series. These values never claim to measure a deployed system.",
    link: null,
  },
  {
    name: "User-supplied CSV diagnostics",
    classification: "Ephemeral user data",
    models: "Pre-registration assessment",
    detail: "CSV uploads are parsed in memory for missingness, duplicate, class-balance, identifier, protected-field, and leakage diagnostics. Files are not written to disk or added to the model registry.",
    processing: "The API limits uploads to 20 MB and returns aggregate diagnostics. The request body is discarded when processing completes.",
    link: null,
  },
];

const REGULATORY_SOURCES = [
  {
    authority: "Reserve Bank of India",
    title: "Draft Guidance on Regulatory Principles for Model Risk Management, 2026",
    status: "Draft; consultation closed 24 July 2026",
    use: "Inventory, tiering, validation independence, monitoring, explainability, overrides, and accountable governance.",
    href: "https://rbidocs.rbi.org.in/rdocs/Content/PDFs/DRAFTGUIDANCE24062026FF12A4FF7BC84E8887009D5C5365F8BF.PDF",
  },
  {
    authority: "Reserve Bank of India",
    title: "FREE-AI Committee Report, 2025",
    status: "Committee report; directional rather than binding law",
    use: "Fairness, accountability, transparency, privacy, trustworthy AI, human oversight, and resilience.",
    href: "https://www.rbi.org.in/Scripts/BS_ViewPublicationReport.aspx",
  },
  {
    authority: "Securities and Exchange Board of India",
    title: "Responsibility for the use of artificial intelligence",
    status: "Binding amendments effective 10 February 2025",
    use: "Responsibility for data privacy, security and integrity, AI outputs, and legal compliance—including third-party tools.",
    href: "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739276753544.pdf",
  },
  {
    authority: "MeitY / Government of India",
    title: "Digital Personal Data Protection Act and Rules",
    status: "Act enacted; 2025 Rules use phased commencement",
    use: "Notice, lawful purpose, minimisation, retention, safeguards, breach response, and data-principal rights.",
    href: "https://www.meity.gov.in/documents/act-and-policies",
  },
  {
    authority: "European Union",
    title: "Regulation (EU) 2024/1689 — Artificial Intelligence Act",
    status: "Phased obligations; general application from 2 August 2026",
    use: "Territorial scope, risk classification, documentation, human oversight, robustness, cybersecurity, and post-market monitoring.",
    href: "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
  },
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-10">
      <section className="panel rise overflow-hidden p-7 sm:p-9">
        <p className="label text-sky-300">Evidence before conclusions</p>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Data provenance and calculation methodology
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
          This page separates observed data, public benchmark data, synthetic demonstrations,
          user-supplied diagnostics, and calculated projections. A plausible-looking number is
          not evidence unless its origin and transformation can be inspected.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Summary icon={<Database />} label="26 registered models" value="4 use real external datasets; 22 are explicit scenarios" />
          <Summary icon={<LineChart />} label="Forecasts" value="Weighted trend + 95% uncertainty, never a guarantee" />
          <Summary icon={<Scale />} label="Regulation" value="Primary sources with status and applicability shown" />
        </div>
      </section>

      <section>
        <SectionTitle icon={<Database />} eyebrow="Provenance" title="Where every category of data comes from" />
        <div className="mt-4 space-y-3">
          {DATA_SOURCES.map((source) => (
            <article key={source.name} className="panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-white">{source.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">Used by: {source.models}</p>
                </div>
                <span className="chip bg-sky-400/[0.06] text-sky-200 ring-sky-400/20">{source.classification}</span>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <MethodBlock label="What is collected" text={source.detail} />
                <MethodBlock label="How it is processed" text={source.processing} />
              </div>
              {source.link && <SourceLink href={source.link} />}
            </article>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle icon={<FlaskConical />} eyebrow="Calculations" title="How registry scores and forecasts are calculated" />
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Calculation title="Governance score" formula="score = sum(available dimensions) / count(available dimensions)">
            The five dimensions are efficiency, adoption, input quality, cost reduction, and revenue impact,
            each constrained to 0–10. Missing dimensions are excluded rather than silently treated as zero.
            Production gates are 5.0 for low-risk, 7.0 for medium-risk, and 8.5 for high-risk models.
          </Calculation>
          <Calculation title="Risk-tier gate" formula="allowed = valid transition AND score ≥ tier threshold">
            Lifecycle transitions are checked by the FastAPI state machine. A high score cannot skip review,
            and a legal transition cannot bypass the score threshold. Emergency shutdown is a separate,
            authenticated path that only moves a model out of production.
          </Calculation>
          <Calculation title="Metric projection" formula="ŷ(t) = β₀ + β₁t, with weights increasing from 0.55 to 1.00">
            Each metric needs at least three distinct timestamps. Recent observations receive more weight,
            but older history still contributes. The system projects 7–90 days and clamps ratio-like metrics
            to 0–1. It does not call an LLM or invent external future events.
          </Calculation>
          <Calculation title="Uncertainty and direction" formula="band = ŷ ± 1.96 × residual σ × √(1 + step/n)">
            The widening band communicates model residual uncertainty. Direction is stable inside a tolerance
            based on 2% of the latest value and historical noise. For latency, errors, drift, complaints,
            hallucinations, and false positives, a downward trend is treated as improvement.
          </Calculation>
          <Calculation title="Forecast confidence" formula="confidence = f(number of observations, residual noise / observed range)">
            High confidence requires at least 20 observations and low normalised residual noise; medium needs
            at least eight and moderate noise. This describes trend fit—not certainty about future reality.
          </Calculation>
          <Calculation title="Readiness priority" formula="urgent = high risk AND any worsening forecast">
            High-risk models or any worsening metric receive elevated review priority; the combination is urgent.
            This is workflow triage, not a probability of regulatory breach or model failure.
          </Calculation>
        </div>
      </section>

      <section>
        <SectionTitle icon={<Scale />} eyebrow="Regulatory mapping" title="Sources used for the regulatory outlook" />
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
          The outlook matches a model’s use case, sector, personal-data exposure, risk tier, and recorded deployment
          regions to a curated watchlist. It does not scrape headlines or claim to forecast what a regulator will enact.
        </p>
        <div className="mt-4 grid gap-3">
          {REGULATORY_SOURCES.map((source) => (
            <article key={source.title} className="panel p-5">
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                <div>
                  <p className="label">{source.authority}</p>
                  <h3 className="mt-1 text-sm font-semibold text-white">{source.title}</h3>
                  <p className="mt-2 text-xs text-amber-200/70">{source.status}</p>
                  <p className="mt-3 text-sm leading-6 text-slate-500">{source.use}</p>
                </div>
                <a href={source.href} target="_blank" rel="noreferrer" className="btn-ghost h-fit text-xs">
                  Primary source <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel border-amber-400/15 bg-amber-400/[0.025] p-6">
        <SectionTitle icon={<ShieldCheck />} eyebrow="Limits" title="What these numbers cannot establish" />
        <ul className="mt-4 grid gap-3 text-sm leading-6 text-slate-400 md:grid-cols-2">
          <li>• Synthetic metrics demonstrate software behaviour; they do not validate a real bank model.</li>
          <li>• A linear trend cannot foresee incidents, retraining, policy intervention, or structural breaks.</li>
          <li>• A confidence band describes residual variation under this method, not all future uncertainty.</li>
          <li>• Regulatory mappings are engineering aids and require qualified legal and compliance review.</li>
          <li>• Registry scores support governance decisions; they do not replace independent validation.</li>
          <li>• External datasets retain their providers’ terms, limitations, update schedules, and outages.</li>
        </ul>
      </section>
    </div>
  );
}

function Summary({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="rounded-lg border border-white/[0.07] bg-ink-900/35 p-4">
    <span className="block h-4 w-4 text-sky-300">{icon}</span>
    <p className="mt-3 text-xs font-medium text-slate-200">{label}</p>
    <p className="mt-1 text-[11px] leading-5 text-slate-600">{value}</p>
  </div>;
}

function SectionTitle({ icon, eyebrow, title }: { icon: React.ReactNode; eyebrow: string; title: string }) {
  return <div className="flex items-start gap-3">
    <span className="mt-0.5 grid h-9 w-9 place-items-center rounded-lg bg-white/[0.04] text-sky-300 ring-1 ring-inset ring-white/[0.07] [&>svg]:h-4 [&>svg]:w-4">{icon}</span>
    <div><p className="label">{eyebrow}</p><h2 className="mt-1 text-lg font-semibold text-white">{title}</h2></div>
  </div>;
}

function MethodBlock({ label, text }: { label: string; text: string }) {
  return <div><p className="label">{label}</p><p className="mt-2 text-sm leading-6 text-slate-500">{text}</p></div>;
}

function Calculation({ title, formula, children }: { title: string; formula: string; children: React.ReactNode }) {
  return <article className="panel p-5">
    <h3 className="text-sm font-semibold text-white">{title}</h3>
    <code className="mt-3 block overflow-x-auto rounded-lg bg-ink-950/70 px-3 py-2 text-[11px] text-sky-200">{formula}</code>
    <p className="mt-3 text-sm leading-6 text-slate-500">{children}</p>
  </article>;
}

function SourceLink({ href }: { href: string }) {
  return <a href={href} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs text-sky-300 hover:text-sky-200">
    Provider documentation <ExternalLink className="h-3 w-3" />
  </a>;
}
