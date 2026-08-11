"use client";

import { useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileUp,
  Info,
  Layers,
  Loader2,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";

import { ApiError } from "@/lib/api";
import {
  DEFAULT_PROPOSAL,
  runAssessment,
  runDatasetDiagnostics,
  SEVERITY_META,
  type AssessmentResult,
  type DatasetResult,
  type Finding,
  type Proposal,
} from "@/lib/assessment";
import { RISK_META } from "@/lib/display";
import { TextReveal } from "@/components/TextReveal";
import { FindingCard } from "@/components/FindingCard";
import { Reveal } from "@/components/Motion";

export default function AssessPage() {
  const [p, setP] = useState<Proposal>(DEFAULT_PROPOSAL);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [dataset, setDataset] = useState<DatasetResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  function set<K extends keyof Proposal>(key: K, value: Proposal[K]) {
    setP((prev) => ({ ...prev, [key]: value }));
  }

  async function submit() {
    if (!p.name.trim() || !p.use_case.trim()) {
      setError("Give the model a name and describe what it does.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    setDataset(null);

    try {
      // Governance first — it's fast and always available. The dataset pass is
      // optional, and a parse failure there shouldn't discard a valid
      // governance assessment the person already waited for.
      const assessment = await runAssessment(p);
      setResult(assessment);

      if (file) {
        try {
          setDataset(await runDatasetDiagnostics(file));
        } catch (e) {
          setError(
            `Governance assessment completed, but the dataset could not be analysed: ${
              e instanceof ApiError ? e.message : String(e)
            }`
          );
        }
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const allFindings: Finding[] = useMemo(() => {
    const combined = [...(result?.findings ?? []), ...(dataset?.findings ?? [])];
    return combined.sort(
      (a, b) => SEVERITY_META[a.severity].order - SEVERITY_META[b.severity].order
    );
  }, [result, dataset]);

  return (
    <div className="space-y-8">
      <section className="pb-2 pt-6 sm:pt-10">
        <p className="fade-in label mb-5 text-slate-500">Pre-registration check</p>

        <TextReveal
          as="h1"
          text="Describe a model. Find out what would stop it."
          className="max-w-3xl text-[clamp(1.8rem,4.8vw,3rem)] font-semibold leading-[1.08] tracking-[-0.02em] text-white"
          delay={120}
        />

        <TextReveal
          text="Assessed against the RBI's draft Model Risk Management guidance. Every finding cites the principle it came from."
          className="mt-6 max-w-xl text-sm leading-relaxed text-slate-400"
          delay={560}
          stagger={14}
        />


        <div className="rule mt-8" style={{ animationDelay: "0.5s" }} />
      </section>

      {/* The honesty notice. Placed before the form rather than buried under
          the results, because someone should know what they're getting before
          they fill anything in. */}
      <div className="panel rise flex gap-3 border-amber-400/15 bg-amber-400/[0.03] p-4">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
        <div className="space-y-2 text-xs leading-relaxed text-slate-400">
          <p>
            <b className="text-amber-200">This does not predict failure.</b> There
            is no dataset of models that later broke, so any percentage this
            produced would be invention with a decimal point on it. A black-box
            risk score inside a tool built to argue against black boxes would be
            self-refuting.
          </p>
          <p>
            What it does: applies published regulatory principles as explicit
            rules, and computes real statistics on any dataset you upload. Every
            finding names its source so you can read it and disagree.
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        {/* ---------------- form ---------------- */}
        <div className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <section className="panel p-5">
            <h2 className="text-sm font-semibold text-white">The model</h2>

            <div className="mt-4 space-y-3">
              <Field label="Name">
                <input
                  value={p.name}
                  onChange={(e) => set("name", e.target.value)}
                  placeholder="e.g. merchant-risk-scorer"
                  className="field"
                />
              </Field>

              <Field label="What does it do?">
                <textarea
                  value={p.use_case}
                  onChange={(e) => set("use_case", e.target.value)}
                  rows={3}
                  placeholder="e.g. Scores merchant applications for onboarding risk and auto-declines the bottom decile"
                  className="field resize-none"
                />
              </Field>

              <Field label="Type">
                <select
                  value={p.model_type}
                  onChange={(e) => set("model_type", e.target.value as Proposal["model_type"])}
                  className="field"
                >
                  <option value="traditional_ml">Classic ML (trees, regression)</option>
                  <option value="slm">Small language model</option>
                  <option value="llm">Large language model</option>
                </select>
              </Field>

              <Field label="How much human involvement?">
                <select
                  value={p.autonomy}
                  onChange={(e) => set("autonomy", e.target.value as Proposal["autonomy"])}
                  className="field"
                >
                  <option value="human_in_the_loop">
                    A person approves each decision
                  </option>
                  <option value="human_on_the_loop">
                    A person supervises, spot-checks
                  </option>
                  <option value="fully_automated">
                    Fully automated, no human in the path
                  </option>
                </select>
              </Field>

              <Field label="How is it monitored after deployment?">
                <select
                  value={p.monitoring}
                  onChange={(e) => set("monitoring", e.target.value as Proposal["monitoring"])}
                  className="field"
                >
                  <option value="none">Not monitored</option>
                  <option value="periodic">Reviewed periodically</option>
                  <option value="continuous">Continuously monitored</option>
                </select>
              </Field>

              <Field label="How often is it retrained?">
                <select
                  value={p.retrain_frequency}
                  onChange={(e) =>
                    set("retrain_frequency", e.target.value as Proposal["retrain_frequency"])
                  }
                  className="field"
                >
                  <option value="never">Never — trained once</option>
                  <option value="annually">Annually</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="monthly">Monthly</option>
                  <option value="continuous">Continuously</option>
                </select>
              </Field>
            </div>
          </section>

          <section className="panel p-5">
            <h2 className="text-sm font-semibold text-white">Characteristics</h2>
            <div className="mt-4 space-y-1">
              <Toggle
                checked={p.affects_customer_money}
                onChange={(v) => set("affects_customer_money", v)}
                label="Affects customers' money or credit access"
                hint="Lending, pricing, payments, claims"
              />
              <Toggle
                checked={p.customer_facing}
                onChange={(v) => set("customer_facing", v)}
                label="Customers interact with it directly"
              />
              <Toggle
                checked={p.is_generative}
                onChange={(v) => set("is_generative", v)}
                label="Generates text, images or code"
              />
              <Toggle
                checked={p.third_party}
                onChange={(v) => set("third_party", v)}
                label="Built or supplied by a third party"
              />
              <Toggle
                checked={p.explainable}
                onChange={(v) => set("explainable", v)}
                label="Individual decisions can be explained"
                hint="Can you say why this specific output happened?"
              />
              <Toggle
                checked={p.independently_validated}
                onChange={(v) => set("independently_validated", v)}
                label="Validated by someone outside the build team"
              />
              <Toggle
                checked={p.has_kill_switch}
                onChange={(v) => set("has_kill_switch", v)}
                label="Has a kill switch"
                hint="Can be switched off immediately, from any state"
              />
              <Toggle
                checked={p.auto_updates}
                onChange={(v) => set("auto_updates", v)}
                label="Updates itself automatically"
              />
              <Toggle
                checked={p.uses_protected_attributes}
                onChange={(v) => set("uses_protected_attributes", v)}
                label="Uses age, gender, location or similar"
              />
              <Toggle
                checked={p.documented_fallback}
                onChange={(v) => set("documented_fallback", v)}
                label="Has a documented fallback if it fails"
              />
            </div>
          </section>

          <section className="panel p-5">
            <h2 className="text-sm font-semibold text-white">
              Dataset <span className="font-normal text-slate-600">(optional)</span>
            </h2>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
              Upload a CSV and it gets checked for overfitting risk, missing
              data, class imbalance, proxy attributes, and — if there&apos;s a
              date column — whether the data already drifts within itself.
              Analysed in memory and never stored.
            </p>

            {file ? (
              <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-white/[0.08] bg-ink-900/50 px-3 py-2.5">
                <span className="truncate font-mono text-xs text-slate-300">
                  {file.name}
                </span>
                <button
                  onClick={() => {
                    setFile(null);
                    if (fileInput.current) fileInput.current.value = "";
                  }}
                  className="shrink-0 text-slate-500 transition hover:text-slate-300"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <label className="mt-4 flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-white/12 px-4 py-6 text-center transition hover:border-white/25 hover:bg-white/[0.02]">
                <FileUp className="h-5 w-5 text-slate-600" />
                <span className="text-xs text-slate-400">
                  Choose a CSV — up to 20MB
                </span>
                <input
                  ref={fileInput}
                  type="file"
                  accept=".csv,.tsv,.txt"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>
            )}
          </section>

          <button onClick={submit} disabled={busy} className="btn-primary w-full">
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Assessing…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run assessment
              </>
            )}
          </button>

          {error && (
            <p className="rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3 text-xs leading-relaxed text-rose-200">
              {error}
            </p>
          )}
        </div>

        {/* ---------------- report ---------------- */}
        <div className="space-y-5">
          {!result ? (
            <div className="panel flex min-h-[320px] flex-col items-center justify-center gap-3 p-10 text-center">
              <Layers className="h-6 w-6 text-slate-700" />
              <p className="max-w-sm text-sm text-slate-500">
                Fill in the form and run the assessment. Findings appear here,
                worst first, each citing the principle behind it.
              </p>
            </div>
          ) : (
            <>
              <Reveal>
                <Verdict result={result} />
              </Reveal>

              {dataset && (
                <Reveal>
                  <DatasetSummary dataset={dataset} />
                </Reveal>
              )}

              <Reveal>
                <div className="space-y-3">
                  <div className="flex items-baseline justify-between gap-3">
                    <h2 className="text-sm font-semibold text-white">
                      Findings
                    </h2>
                    <span className="text-xs text-slate-600">
                      {allFindings.length} total, worst first
                    </span>
                  </div>
                  {allFindings.map((f, i) => (
                    <FindingCard key={`${f.title}-${i}`} finding={f} />
                  ))}
                </div>
              </Reveal>

              <Reveal>
                <div className="panel p-4">
                  <p className="text-[11px] leading-relaxed text-slate-500">
                    Assessed against{" "}
                    <a
                      href={result.source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-sky-400 transition hover:text-sky-300"
                    >
                      {result.source.title}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                    , {result.source.issuer}, {result.source.reference}, dated{" "}
                    {result.source.dated}.{" "}
                    <span className="text-amber-300/80">
                      {result.source.status}.
                    </span>{" "}
                    This is an engineering aid, not legal or regulatory advice.
                  </p>
                </div>
              </Reveal>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="label mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 rounded-lg px-2 py-2 transition hover:bg-white/[0.02]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded border-white/20 bg-transparent accent-sky-500"
      />
      <span>
        <span className="block text-xs text-slate-300">{label}</span>
        {hint && (
          <span className="mt-0.5 block text-[11px] text-slate-600">{hint}</span>
        )}
      </span>
    </label>
  );
}

function Verdict({ result }: { result: AssessmentResult }) {
  const { summary, tiering } = result;
  const tone =
    summary.verdict === "not_ready"
      ? "border-rose-400/20 bg-rose-400/[0.05]"
      : summary.verdict === "significant_gaps"
        ? "border-amber-400/20 bg-amber-400/[0.05]"
        : summary.verdict === "conditional"
          ? "border-sky-400/20 bg-sky-400/[0.05]"
          : "border-emerald-400/20 bg-emerald-400/[0.05]";

  const Icon =
    summary.verdict === "sound"
      ? CheckCircle2
      : summary.verdict === "not_ready"
        ? ShieldAlert
        : AlertTriangle;

  const risk = RISK_META[tiering.tier];

  return (
    <div className={`panel border p-5 ${tone}`}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0 text-slate-300" />
        <div>
          <h2 className="text-base font-semibold text-white">
            {summary.headline}
          </h2>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
            {summary.detail}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 border-t border-white/[0.08] pt-4 sm:grid-cols-2">
        <div>
          <p className="label">Recommended risk tier</p>
          <p className="mt-2">
            <span className={`chip ${risk.chip}`}>{risk.label}</span>
          </p>
          <p className="mt-2.5 text-[11px] leading-relaxed text-slate-500">
            {tiering.rationale}
          </p>
          {tiering.anti_dilution_applied && (
            <p className="mt-2 rounded-lg border border-white/[0.06] bg-ink-900/40 px-3 py-2 text-[11px] leading-relaxed text-slate-400">
              Anti-dilution rule applied: this model is simple but consequential,
              so the tier follows materiality rather than being averaged down by
              a low complexity score.
            </p>
          )}
        </div>

        <div>
          <p className="label">Findings by severity</p>
          <ul className="mt-2 space-y-1.5">
            {(["blocker", "high", "medium", "info"] as const).map((s) => (
              <li key={s} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-xs text-slate-400">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${SEVERITY_META[s].dot}`}
                  />
                  {SEVERITY_META[s].label}
                </span>
                <span className="font-mono text-xs tabular-nums text-slate-300">
                  {summary.counts[s]}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 space-y-1.5 border-t border-white/[0.08] pt-4">
        {tiering.materiality.reasons.length > 0 && (
          <p className="text-[11px] text-slate-500">
            <span className="text-slate-400">Materiality:</span>{" "}
            {tiering.materiality.reasons.join("; ")}.
          </p>
        )}
        {tiering.complexity.reasons.length > 0 && (
          <p className="text-[11px] text-slate-500">
            <span className="text-slate-400">Complexity:</span>{" "}
            {tiering.complexity.reasons.join("; ")}.
          </p>
        )}
      </div>
    </div>
  );
}

function DatasetSummary({ dataset }: { dataset: DatasetResult }) {
  const { stats, drift } = dataset;

  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-white">Dataset diagnostics</h2>
        <span className="font-mono text-[11px] text-slate-600">
          {dataset.filename}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Rows" value={stats.rows.toLocaleString()} />
        <Stat label="Columns" value={String(stats.columns)} />
        <Stat label="Rows per feature" value={String(stats.rows_per_feature)} />
        <Stat
          label="Target found"
          value={stats.detected_target ?? "—"}
          mono={Boolean(stats.detected_target)}
        />
      </dl>

      {drift ? (
        <div className="mt-5 border-t border-white/[0.06] pt-4">
          <p className="label">
            Drift within the file — {drift.early_period} to {drift.late_period}
          </p>
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            The file was split at {drift.split_at} and each feature compared
            across the two halves using Population Stability Index. Above 0.25
            counts as a significant shift.
          </p>

          <ul className="mt-4 space-y-2">
            {Object.entries(drift.per_feature_psi)
              .slice(0, 8)
              .map(([feature, psi]) => {
                const tone =
                  psi >= 0.25
                    ? "bg-rose-400"
                    : psi >= 0.1
                      ? "bg-amber-400"
                      : "bg-emerald-400";
                return (
                  <li key={feature}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate font-mono text-[11px] text-slate-400">
                        {feature}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-slate-300">
                        {psi.toFixed(3)}
                      </span>
                    </div>
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/[0.06]">
                      <div
                        className={`grow h-full rounded-full ${tone}`}
                        style={{ width: `${Math.min(psi / 0.5, 1) * 100}%` }}
                      />
                    </div>
                  </li>
                );
              })}
          </ul>
        </div>
      ) : (
        <p className="mt-4 border-t border-white/[0.06] pt-4 text-xs leading-relaxed text-slate-500">
          No usable date column, so drift within the file couldn&apos;t be
          measured — that&apos;s the most informative check available and it
          needs a timestamp to work.
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="label">{label}</dt>
      <dd
        className={`mt-1.5 truncate text-sm text-slate-200 ${mono ? "font-mono text-xs" : ""}`}
        title={value}
      >
        {value}
      </dd>
    </div>
  );
}
