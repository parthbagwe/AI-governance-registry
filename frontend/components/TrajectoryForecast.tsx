"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Scale, Sparkles } from "lucide-react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDay, METRIC_GLOSS } from "@/lib/display";
import type { ModelForecast, ModelMetric } from "@/lib/types";

const TRAJECTORY_META = {
  improving: { label: "Improving", colour: "text-emerald-300", dot: "bg-emerald-300" },
  stable: { label: "Stable", colour: "text-sky-300", dot: "bg-sky-300" },
  worsening: { label: "Worsening", colour: "text-rose-300", dot: "bg-rose-300" },
};

export function TrajectoryForecast({
  metrics,
  outlook,
}: {
  metrics: ModelMetric[];
  outlook: ModelForecast;
}) {
  const [selected, setSelected] = useState(outlook.forecasts[0]?.metric_name ?? "");
  const active = outlook.forecasts.find((item) => item.metric_name === selected)
    ?? outlook.forecasts[0];

  useEffect(() => {
    if (!outlook.forecasts.some((item) => item.metric_name === selected)) {
      setSelected(outlook.forecasts[0]?.metric_name ?? "");
    }
  }, [outlook, selected]);

  const chartData = useMemo(() => {
    if (!active) return [];
    const actual = metrics
      .filter((item) => item.metric_name === active.metric_name)
      .slice(-45)
      .map((item) => ({
        recorded_at: item.recorded_at,
        observed: item.metric_value,
      }));
    const bridge = {
      recorded_at: active.last_observed_at,
      projected: active.last_observed_value,
      range: [active.last_observed_value, active.last_observed_value],
    };
    const projected = active.forecast_points.map((point) => ({
      recorded_at: point.recorded_at,
      projected: point.predicted_value,
      range: [point.lower_bound, point.upper_bound],
    }));
    return [...actual, bridge, ...projected].sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    );
  }, [active, metrics]);

  const priorityClass = outlook.readiness_priority === "urgent"
    ? "text-rose-200 ring-rose-400/25 bg-rose-400/[0.07]"
    : outlook.readiness_priority === "elevated"
      ? "text-amber-200 ring-amber-400/25 bg-amber-400/[0.07]"
      : "text-emerald-200 ring-emerald-400/25 bg-emerald-400/[0.07]";

  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-white/[0.06] p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-sky-300" />
              <h2 className="text-sm font-semibold text-white">AI trajectory & regulatory outlook</h2>
            </div>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
              Observed history is solid; the dashed line is a transparent statistical projection.
              The band shows uncertainty, while regulatory cards describe sourced scenarios—not predicted law.
            </p>
          </div>
          <span className={`chip capitalize ${priorityClass}`}>
            {outlook.readiness_priority} readiness priority
          </span>
        </div>
      </div>

      <div className="grid gap-6 p-5 xl:grid-cols-[1.3fr_1fr]">
        <div>
          {active ? (
            <>
              <div className="flex flex-wrap gap-2">
                {outlook.forecasts.map((item) => (
                  <button key={item.metric_name} onClick={() => setSelected(item.metric_name)}
                    className={`chip transition ${selected === item.metric_name
                      ? "bg-white/[0.08] text-white ring-white/15"
                      : "text-slate-500 ring-white/[0.07] hover:text-slate-300"}`}>
                    {item.metric_name}
                  </button>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
                <span className={TRAJECTORY_META[active.trajectory].colour}>
                  <span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${TRAJECTORY_META[active.trajectory].dot}`} />
                  {TRAJECTORY_META[active.trajectory].label}
                </span>
                <span className="text-slate-500">{active.confidence} confidence</span>
                <span className="text-slate-500">{active.historical_points} observations</span>
                <span className="text-slate-500">{outlook.horizon_days}-day horizon</span>
              </div>

              <div className="mt-3 h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                    <CartesianGrid stroke="rgba(148,163,184,0.10)" vertical={false} />
                    <XAxis dataKey="recorded_at" tickFormatter={(value) => formatDay(String(value))}
                      stroke="#475569" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={28} />
                    <YAxis stroke="#475569" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={56} />
                    <Tooltip contentStyle={{ background: "#0d1220", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, fontSize: 12 }}
                      labelFormatter={(value) => formatDay(String(value))} labelStyle={{ color: "#94a3b8" }} />
                    <Area type="monotone" dataKey="range" stroke="none" fill="#38bdf8" fillOpacity={0.1}
                      name="95% uncertainty" connectNulls />
                    <Line type="monotone" dataKey="observed" stroke="#e2e8f0" strokeWidth={2}
                      dot={false} name="Observed" connectNulls />
                    <Line type="monotone" dataKey="projected" stroke="#38bdf8" strokeWidth={2}
                      strokeDasharray="7 6" dot={false} name="Projected" connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <p className="mt-2 text-[11px] leading-relaxed text-slate-600">
                {METRIC_GLOSS[active.metric_name] ?? active.metric_name}. {outlook.method}.
                {" "}{outlook.disclaimer}
              </p>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-white/10 p-6 text-sm text-slate-500">
              At least three dated measurements are needed before a trajectory can be projected.
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-amber-300" />
            <h3 className="text-sm font-semibold text-white">Regulatory scope</h3>
          </div>
          <p className="mt-1 text-[11px] text-slate-600">Source review current to {outlook.regulatory_as_of}.</p>

          <div className="mt-4 max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {outlook.regulatory_signals.map((signal) => (
              <article key={`${signal.authority}-${signal.title}`}
                className="rounded-lg border border-white/[0.07] bg-ink-900/35 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-slate-600">{signal.authority}</p>
                    <h4 className="mt-1 text-xs font-medium leading-relaxed text-slate-200">{signal.title}</h4>
                  </div>
                  <span className="chip shrink-0 capitalize bg-white/[0.04] text-slate-400 ring-white/[0.08]">
                    {signal.applicability}
                  </span>
                </div>
                <p className="mt-2 text-[11px] text-amber-200/70">{signal.status}</p>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">{signal.model_impact}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {signal.likely_control_scope.map((scope) => (
                    <span key={scope} className="rounded-full bg-white/[0.04] px-2 py-1 text-[10px] text-slate-500">{scope}</span>
                  ))}
                </div>
                <a href={signal.source_url} target="_blank" rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-[11px] text-sky-300 transition hover:text-sky-200">
                  Primary source <ExternalLink className="h-3 w-3" />
                </a>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
