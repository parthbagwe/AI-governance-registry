/**
 * These types mirror the Pydantic response schemas in app/schemas.py exactly.
 * Keeping them in one file means a backend field rename shows up as a
 * TypeScript error here rather than as a silent `undefined` in the UI.
 */

export type ModelType = "traditional_ml" | "slm" | "llm";
export type ModelStage = "pilot" | "review" | "production" | "deprecated";
export type RiskTier = "low" | "medium" | "high";

export interface MLModel {
  id: string;
  name: string;
  version: string;
  model_type: ModelType;
  use_case: string;
  owner: string;
  stage: ModelStage;
  risk_tier: RiskTier;
  efficiency_score: number | null;
  adoption_score: number | null;
  input_quality_score: number | null;
  cost_reduction_score: number | null;
  revenue_impact_score: number | null;
  governance_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface ModelMetric {
  metric_name: string;
  metric_value: number;
  recorded_at: string;
}

export interface ApprovalEvent {
  from_stage: ModelStage | null;
  to_stage: ModelStage;
  approved_by: string;
  comment: string | null;
  is_emergency: boolean;
  created_at: string;
}

export interface DataLineage {
  source_table: string;
  features_used: string[];
  notes: string | null;
}

export interface ExplainFactor {
  feature: string;
  value: number;
  impact: number;
  direction: "increased_risk" | "decreased_risk";
}

export interface ExplainResult {
  predicted_default_probability: number;
  decision: string;
  top_factors: ExplainFactor[];
}

/** The five governance-scorecard dimensions, in display order. */
export const SCORE_DIMENSIONS: {
  key: keyof Pick<
    MLModel,
    | "efficiency_score"
    | "adoption_score"
    | "input_quality_score"
    | "cost_reduction_score"
    | "revenue_impact_score"
  >;
  label: string;
  plain: string;
}[] = [
  {
    key: "efficiency_score",
    label: "Efficiency",
    plain: "Does it actually save time or effort?",
  },
  {
    key: "adoption_score",
    label: "Adoption",
    plain: "Are the teams meant to use it actually using it?",
  },
  {
    key: "input_quality_score",
    label: "Input Quality",
    plain: "Is the data feeding it clean and trustworthy?",
  },
  {
    key: "cost_reduction_score",
    label: "Cost Reduction",
    plain: "Does it measurably reduce operating cost?",
  },
  {
    key: "revenue_impact_score",
    label: "Revenue Impact",
    plain: "Does it bring in or protect revenue?",
  },
];

/**
 * Mirrors MIN_SCORE_BY_TIER in app/workflow.py. Duplicated here purely so the
 * UI can warn a user *before* they click and get a 403 — the backend remains
 * the single source of truth, and the API's rejection is always authoritative.
 */
export const MIN_SCORE_BY_TIER: Record<RiskTier, number> = {
  low: 5.0,
  medium: 7.0,
  high: 8.5,
};

/** Mirrors ALLOWED_TRANSITIONS in app/workflow.py, for the same reason. */
export const ALLOWED_TRANSITIONS: Record<ModelStage, ModelStage[]> = {
  pilot: ["review", "deprecated"],
  review: ["production", "pilot", "deprecated"],
  production: ["deprecated", "review"],
  deprecated: [],
};
