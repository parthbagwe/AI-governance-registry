import { AlertTriangle } from "lucide-react";
import { RISK_META, STAGE_META } from "@/lib/display";
import type { ModelStage, RiskTier } from "@/lib/types";

export function StageBadge({
  stage,
  className = "",
}: {
  stage: ModelStage;
  className?: string;
}) {
  const meta = STAGE_META[stage];
  return (
    <span className={`chip ${meta.chip} ${className}`} title={meta.plain}>
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}

export function RiskBadge({
  tier,
  className = "",
}: {
  tier: RiskTier;
  className?: string;
}) {
  const meta = RISK_META[tier];
  return (
    <span className={`chip ${meta.chip} ${className}`} title={meta.plain}>
      {tier === "high" && <AlertTriangle className="h-3 w-3" />}
      {meta.label}
    </span>
  );
}
