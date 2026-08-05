"use client";

import { useState } from "react";
import { Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { ExplainResult } from "@/lib/types";

/**
 * Only wired up for sme-credit-scorer, matching the backend's own restriction.
 *
 * The point of surfacing this in the UI rather than leaving it as a script is
 * that "why was this applicant flagged" is a question a reviewer asks, not a
 * question a data scientist runs on their laptop. RBI's draft guidance treats
 * explainability as a property of the model, not an optional side tool.
 */

const FIELDS: {
  key: string;
  label: string;
  hint: string;
  step: number;
  initial: number;
}[] = [
  {
    key: "avg_monthly_turnover",
    label: "Average monthly turnover",
    hint: "Business revenue per month, in rupees",
    step: 10000,
    initial: 850000,
  },
  {
    key: "filing_delay_days",
    label: "GST filing delay",
    hint: "Average days late on tax filings",
    step: 1,
    initial: 12,
  },
  {
    key: "itc_claim_ratio",
    label: "Input tax credit claim ratio",
    hint: "Between 0 and 1",
    step: 0.05,
    initial: 0.55,
  },
  {
    key: "avg_balance",
    label: "Average bank balance",
    hint: "Typical balance held, in rupees",
    step: 5000,
    initial: 95000,
  },
  {
    key: "inflow_volatility",
    label: "Income volatility",
    hint: "Higher means less predictable income",
    step: 0.1,
    initial: 0.6,
  },
  {
    key: "bounce_count_90d",
    label: "Bounced payments (90 days)",
    hint: "Count of failed payments recently",
    step: 1,
    initial: 2,
  },
];

export function ExplainPanel({ modelId }: { modelId: string }) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f.key, f.initial]))
  );
  const [result, setResult] = useState<ExplainResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.explain(modelId, values));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  const flagged = result?.decision?.includes("HIGHER RISK");
  const maxImpact = result
    ? Math.max(...result.top_factors.map((f) => Math.abs(f.impact)), 0.0001)
    : 1;

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-violet-400" />
        <h2 className="text-sm font-semibold text-white">Explain a decision</h2>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-slate-500">
        Enter a business&apos;s details and the model will show not just its
        verdict, but which specific factors drove it and by how much. No
        black-box answers.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <div key={f.key}>
            <label className="label mb-1.5 block">{f.label}</label>
            <input
              type="number"
              step={f.step}
              value={values[f.key]}
              onChange={(e) =>
                setValues((v) => ({ ...v, [f.key]: Number(e.target.value) }))
              }
              className="field font-mono"
            />
            <p className="mt-1 text-[11px] text-slate-600">{f.hint}</p>
          </div>
        ))}
      </div>

      <button onClick={run} disabled={busy} className="btn-primary mt-4">
        {busy ? "Analysing…" : "Explain this decision"}
      </button>

      {error && (
        <p className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3 text-xs text-rose-200">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-5 space-y-4">
          <div
            className={`rounded-lg border px-4 py-3 ${
              flagged
                ? "border-rose-400/20 bg-rose-400/[0.06]"
                : "border-emerald-400/20 bg-emerald-400/[0.06]"
            }`}
          >
            <p className="label">Verdict</p>
            <p
              className={`mt-1 text-lg font-semibold ${
                flagged ? "text-rose-200" : "text-emerald-200"
              }`}
            >
              {flagged ? "Flagged as higher risk" : "Looks acceptable"}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Estimated chance of default:{" "}
              <span className="font-mono">
                {(result.predicted_default_probability * 100).toFixed(1)}%
              </span>
            </p>
          </div>

          <div>
            <p className="label mb-3">Why — ranked by influence</p>
            <ul className="space-y-2.5">
              {result.top_factors.map((f) => {
                const up = f.direction === "increased_risk";
                const width = (Math.abs(f.impact) / maxImpact) * 100;
                return (
                  <li key={f.feature}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="flex items-center gap-1.5 text-sm text-slate-300">
                        {up ? (
                          <TrendingUp className="h-3.5 w-3.5 text-rose-400" />
                        ) : (
                          <TrendingDown className="h-3.5 w-3.5 text-emerald-400" />
                        )}
                        {FIELDS.find((x) => x.key === f.feature)?.label ??
                          f.feature}
                      </span>
                      <span className="font-mono text-xs tabular-nums text-slate-500">
                        {f.value.toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                      <div
                        className={`h-full rounded-full ${
                          up ? "bg-rose-400" : "bg-emerald-400"
                        }`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[11px] text-slate-600">
                      {up ? "Pushed risk up" : "Pushed risk down"} by{" "}
                      <span className="font-mono">
                        {f.impact >= 0 ? "+" : ""}
                        {f.impact.toFixed(3)}
                      </span>
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
