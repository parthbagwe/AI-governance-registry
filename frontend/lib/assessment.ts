import { API_BASE, ApiError } from "@/lib/api";

export type Severity = "blocker" | "high" | "medium" | "info";

export interface Finding {
  severity: Severity;
  title: string;
  detail: string;
  action: string;
  principle: string;
  reference: string;
  evidence: string | null;
}

export interface Proposal {
  name: string;
  use_case: string;
  model_type: "traditional_ml" | "slm" | "llm";
  is_generative: boolean;
  third_party: boolean;
  customer_facing: boolean;
  affects_customer_money: boolean;
  autonomy: "human_in_the_loop" | "human_on_the_loop" | "fully_automated";
  explainable: boolean;
  auto_updates: boolean;
  has_kill_switch: boolean;
  independently_validated: boolean;
  monitoring: "none" | "periodic" | "continuous";
  retrain_frequency: "never" | "annually" | "quarterly" | "monthly" | "continuous";
  uses_protected_attributes: boolean;
  documented_fallback: boolean;
}

export interface AssessmentResult {
  source: {
    title: string;
    issuer: string;
    reference: string;
    dated: string;
    status: string;
    url: string;
  };
  tiering: {
    tier: "low" | "medium" | "high";
    materiality: { band: string; score: number; reasons: string[] };
    complexity: { band: string; score: number; reasons: string[] };
    anti_dilution_applied: boolean;
    rationale: string;
  };
  summary: {
    verdict: "not_ready" | "significant_gaps" | "conditional" | "sound";
    headline: string;
    detail: string;
    counts: Record<Severity, number>;
    tier: string;
  };
  findings: Finding[];
}

export interface DatasetResult {
  filename: string;
  stats: {
    rows: number;
    columns: number;
    rows_per_feature: number;
    columns_with_missing: number;
    worst_missing: { column: string; share: number } | null;
    protected_candidates: string[];
    detected_target: string | null;
    positive_rate?: number;
    date_column: string | null;
  };
  drift: {
    date_column: string;
    early_period: string;
    split_at: string;
    late_period: string;
    per_feature_psi: Record<string, number>;
    shifted_share: number;
    significant: string[];
  } | null;
  findings: Finding[];
}

export const DEFAULT_PROPOSAL: Proposal = {
  name: "",
  use_case: "",
  model_type: "traditional_ml",
  is_generative: false,
  third_party: false,
  customer_facing: false,
  affects_customer_money: false,
  autonomy: "human_in_the_loop",
  explainable: true,
  auto_updates: false,
  has_kill_switch: false,
  independently_validated: false,
  monitoring: "none",
  retrain_frequency: "never",
  uses_protected_attributes: false,
  documented_fallback: false,
};

export async function runAssessment(p: Proposal): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/assessment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.detail ?? "Assessment failed");
  }
  return res.json();
}

export async function runDatasetDiagnostics(file: File): Promise<DatasetResult> {
  const form = new FormData();
  form.append("file", file);
  // No Content-Type header — the browser has to set the multipart boundary
  // itself, and setting it manually produces a request the server can't parse.
  const res = await fetch(`${API_BASE}/assessment/dataset`, {
    method: "POST",
    body: form,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.detail ?? "Could not analyse that file");
  }
  return res.json();
}

export const SEVERITY_META: Record<
  Severity,
  { label: string; chip: string; dot: string; order: number }
> = {
  blocker: {
    label: "Blocker",
    chip: "bg-rose-500/10 text-rose-300 ring-rose-400/25",
    dot: "bg-rose-400",
    order: 0,
  },
  high: {
    label: "High",
    chip: "bg-amber-500/10 text-amber-300 ring-amber-400/25",
    dot: "bg-amber-400",
    order: 1,
  },
  medium: {
    label: "Medium",
    chip: "bg-sky-500/10 text-sky-300 ring-sky-400/25",
    dot: "bg-sky-400",
    order: 2,
  },
  info: {
    label: "Note",
    chip: "bg-slate-500/10 text-slate-400 ring-slate-500/25",
    dot: "bg-slate-500",
    order: 3,
  },
};
