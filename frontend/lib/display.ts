/**
 * Display-layer translation only.
 *
 * The backend keeps its precise, technical vocabulary (`production`,
 * `governance_score`, `high` risk tier). This file translates that into
 * language a risk-committee member or branch manager can read without a
 * glossary. Nothing here changes what gets sent to the API — the values on
 * the wire stay exactly as the backend defines them.
 */

import type { ModelStage, ModelType, RiskTier } from "./types";

export const STAGE_META: Record<
  ModelStage,
  { label: string; plain: string; dot: string; chip: string }
> = {
  pilot: {
    label: "Testing",
    plain: "Being trialled. Not making real decisions yet.",
    dot: "bg-amber-400",
    chip: "bg-amber-400/10 text-amber-300 ring-amber-400/25",
  },
  review: {
    label: "Under Review",
    plain: "Waiting on an independent sign-off before it can go live.",
    dot: "bg-sky-400",
    chip: "bg-sky-400/10 text-sky-300 ring-sky-400/25",
  },
  production: {
    label: "Live",
    plain: "Actively making decisions that affect customers today.",
    dot: "bg-emerald-400",
    chip: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/25",
  },
  deprecated: {
    label: "Retired",
    plain: "Switched off. Kept on record for audit purposes.",
    dot: "bg-slate-500",
    chip: "bg-slate-500/10 text-slate-400 ring-slate-500/25",
  },
};

export const RISK_META: Record<
  RiskTier,
  { label: string; plain: string; chip: string }
> = {
  low: {
    label: "Low risk",
    plain: "Limited impact if it gets something wrong — e.g. an internal FAQ bot.",
    chip: "bg-slate-500/10 text-slate-300 ring-slate-500/25",
  },
  medium: {
    label: "Medium risk",
    plain: "Commercial impact, but no direct effect on a customer's money.",
    chip: "bg-amber-500/10 text-amber-300 ring-amber-500/25",
  },
  high: {
    label: "High risk",
    plain: "Directly affects customers' money or the bank's compliance position.",
    chip: "bg-rose-500/10 text-rose-300 ring-rose-500/25",
  },
};

export const TYPE_LABEL: Record<ModelType, string> = {
  traditional_ml: "Classic ML",
  slm: "Small language model",
  llm: "Large language model",
};

/** Traffic-light reading of a governance score, so a raw number isn't required. */
export function scoreHealth(score: number | null): {
  label: string;
  tone: string;
  ring: string;
} {
  if (score === null)
    return {
      label: "Not yet scored",
      tone: "text-slate-400",
      ring: "ring-slate-600/40",
    };
  if (score >= 8.5)
    return { label: "Strong", tone: "text-emerald-300", ring: "ring-emerald-400/30" };
  if (score >= 7)
    return { label: "Adequate", tone: "text-sky-300", ring: "ring-sky-400/30" };
  if (score >= 5)
    return { label: "Needs work", tone: "text-amber-300", ring: "ring-amber-400/30" };
  return { label: "Weak", tone: "text-rose-300", ring: "ring-rose-400/30" };
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDay(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Turns `avg_monthly_turnover` into `Avg monthly turnover`. */
export function humaniseField(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Plain-English gloss for the metric names the backend logs. */
export const METRIC_GLOSS: Record<string, string> = {
  accuracy: "How often the model's call is correct",
  real_accuracy: "Accuracy measured on the actual trained model",
  auc: "How well it separates risky from safe cases (0.5 = coin flip)",
  precision: "Of the cases it flagged, how many were genuinely risky",
  recall: "Of the genuinely risky cases, how many it caught",
  latency_ms: "How long a single decision takes, in milliseconds",
  drift_share: "Share of inputs that have shifted away from training data",
  fairness_ratio: "Approval-rate parity between customer segments (1.0 = equal)",
  anomaly_rate: "Share of live transactions flagged as unusual",
  mean_anomaly_score: "Average unusualness across the batch",
  p99_anomaly_score: "How extreme the most unusual 1% were",
  live_batch_size: "Transactions pulled from the live feed this run",
  baseline_sample_size: "Transactions the model learned 'normal' from",
};
