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

/**
 * Marks a model whose data arrives continuously. The pulse is the point: a
 * static badge saying "live" is a claim, an animating one is closer to
 * evidence that something is still moving.
 */
export function LiveBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`chip bg-emerald-400/10 text-emerald-300 ring-emerald-400/25 ${className}`}
      title="Fed by a live data feed — refreshed every monitoring run"
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
      </span>
      Live
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
