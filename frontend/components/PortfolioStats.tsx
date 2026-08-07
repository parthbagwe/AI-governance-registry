import { Activity, AlertTriangle, ClipboardCheck, Layers } from "lucide-react";
import type { MLModel } from "@/lib/types";
import { CountUp } from "@/components/Motion";

/**
 * The four numbers a risk committee actually opens this page to see, before
 * they look at any individual model.
 */
export function PortfolioStats({ models }: { models: MLModel[] }) {
  const live = models.filter((m) => m.stage === "production").length;
  const awaiting = models.filter((m) => m.stage === "review").length;
  const highRisk = models.filter(
    (m) => m.risk_tier === "high" && m.stage !== "deprecated"
  ).length;

  const cards = [
    {
      label: "Models on record",
      value: models.length,
      note: "Every version, at every stage",
      icon: Layers,
      tone: "text-slate-300 bg-slate-500/10 ring-slate-500/25",
    },
    {
      label: "Live in production",
      value: live,
      note: "Making real decisions today",
      icon: Activity,
      tone: "text-emerald-300 bg-emerald-400/10 ring-emerald-400/25",
    },
    {
      label: "Awaiting sign-off",
      value: awaiting,
      note: "Blocked until a reviewer approves",
      icon: ClipboardCheck,
      tone: "text-sky-300 bg-sky-400/10 ring-sky-400/25",
    },
    {
      label: "High-risk, still active",
      value: highRisk,
      note: "Face the strictest approval bar",
      icon: AlertTriangle,
      tone: "text-rose-300 bg-rose-500/10 ring-rose-400/25",
    },
  ];

  return (
    <div className="stagger grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="panel lift p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="label">{c.label}</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums text-white">
                <CountUp value={c.value} />
              </p>
            </div>
            <span
              className={`grid h-9 w-9 place-items-center rounded-lg ring-1 ring-inset ${c.tone}`}
            >
              <c.icon className="h-4 w-4" />
            </span>
          </div>
          <p className="mt-3 text-xs text-slate-500">{c.note}</p>
        </div>
      ))}
    </div>
  );
}
