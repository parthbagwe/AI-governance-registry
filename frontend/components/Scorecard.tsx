import { MIN_SCORE_BY_TIER, SCORE_DIMENSIONS } from "@/lib/types";
import type { MLModel } from "@/lib/types";
import { scoreHealth } from "@/lib/display";
import { CountUp } from "@/components/Motion";

/**
 * The five-dimension scorecard, shown as bars rather than bare numbers so the
 * weak dimension is obvious at a glance — that's usually the single thing
 * blocking a model from going live.
 */
export function Scorecard({ model }: { model: MLModel }) {
  const required = MIN_SCORE_BY_TIER[model.risk_tier];
  const health = scoreHealth(model.governance_score);
  const clears =
    model.governance_score !== null && model.governance_score >= required;

  return (
    <section className="panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-white">
            Governance scorecard
          </h2>
          <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-500">
            Five checks a model must pass before it can be trusted with real
            decisions. The overall score is their average.
          </p>
        </div>

        <div className="text-right">
          <p
            className={`font-mono text-[2.6rem] font-semibold leading-none tracking-[-0.03em] tabular-nums ${health.tone}`}
          >
            {model.governance_score !== null ? (
              <CountUp value={model.governance_score} decimals={2} />
            ) : (
              "—"
            )}
            <span className="ml-1 text-base text-slate-600">/10</span>
          </p>
          <p className="mt-0.5 text-xs text-slate-500">{health.label}</p>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {SCORE_DIMENSIONS.map((dim) => {
          const value = model[dim.key];
          return (
            <div key={dim.key}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm text-slate-300" title={dim.plain}>
                  {dim.label}
                </span>
                <span className="font-mono text-xs tabular-nums text-slate-400">
                  {value === null ? "not scored" : value.toFixed(1)}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className={`grow h-full rounded-full ${barTone(value)}`}
                  style={{ width: `${((value ?? 0) / 10) * 100}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] text-slate-600">{dim.plain}</p>
            </div>
          );
        })}
      </div>

      <div
        className={`mt-5 rounded-lg border px-4 py-3 text-xs leading-relaxed ${
          clears
            ? "border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200"
            : "border-amber-400/20 bg-amber-400/[0.06] text-amber-200"
        }`}
      >
        {clears ? (
          <>
            Clears the <b>{required.toFixed(1)}</b> bar required for a{" "}
            {model.risk_tier}-risk model. An independent reviewer can approve
            it for live use.
          </>
        ) : (
          <>
            Below the <b>{required.toFixed(1)}</b> bar required for a{" "}
            {model.risk_tier}-risk model. It cannot go live until the weaker
            dimensions above improve — the backend will reject the attempt.
          </>
        )}
      </div>
    </section>
  );
}

function barTone(value: number | null): string {
  if (value === null) return "bg-slate-700";
  if (value >= 8.5) return "bg-emerald-400";
  if (value >= 7) return "bg-sky-400";
  if (value >= 5) return "bg-amber-400";
  return "bg-rose-400";
}
