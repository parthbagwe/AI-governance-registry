"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDay, METRIC_GLOSS } from "@/lib/display";
import type { ModelMetric } from "@/lib/types";
import { Empty } from "@/components/States";

const SERIES_COLOURS = [
  "#38bdf8",
  "#a78bfa",
  "#fbbf24",
  "#34d399",
  "#f472b6",
  "#f87171",
];

/**
 * Renders the time-series in model_metrics. For the credit scorer this is
 * where the injected accuracy drop becomes a visible dip, which is the whole
 * point of pairing drift detection with a chart rather than a log line.
 */
export function MetricChart({ metrics }: { metrics: ModelMetric[] }) {
  const names = useMemo(
    () => Array.from(new Set(metrics.map((m) => m.metric_name))).sort(),
    [metrics]
  );

  const [selected, setSelected] = useState<string[]>(() => {
    const preferred = names.filter((n) =>
      ["accuracy", "real_accuracy"].includes(n)
    );
    return preferred.length ? preferred : names.slice(0, 1);
  });

  // Recharts wants one row per timestamp with a column per series, so the
  // long-format rows coming back from the API get pivoted here.
  const data = useMemo(() => {
    const byTime = new Map<string, Record<string, number | string>>();
    for (const m of metrics) {
      if (!selected.includes(m.metric_name)) continue;
      const row = byTime.get(m.recorded_at) ?? { recorded_at: m.recorded_at };
      row[m.metric_name] = m.metric_value;
      byTime.set(m.recorded_at, row);
    }
    return Array.from(byTime.values()).sort(
      (a, b) =>
        new Date(a.recorded_at as string).getTime() -
        new Date(b.recorded_at as string).getTime()
    );
  }, [metrics, selected]);

  if (metrics.length === 0) {
    return (
      <section className="panel p-5">
        <h2 className="text-sm font-semibold text-white">Performance over time</h2>
        <div className="mt-4">
          <Empty>
            No metrics logged for this model yet. Training and monitoring
            scripts write here as they run.
          </Empty>
        </div>
      </section>
    );
  }

  function toggle(name: string) {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  }

  return (
    <section className="panel p-5">
      <h2 className="text-sm font-semibold text-white">Performance over time</h2>
      <p className="mt-1 text-xs text-slate-500">
        Every measurement the monitoring jobs have recorded. A sustained drop
        here is what triggers an automatic demotion back to review.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {names.map((name, i) => {
          const on = selected.includes(name);
          return (
            <button
              key={name}
              onClick={() => toggle(name)}
              title={METRIC_GLOSS[name] ?? name}
              className={`chip transition ${
                on
                  ? "bg-white/[0.08] text-slate-100 ring-white/15"
                  : "text-slate-500 ring-white/[0.07] hover:text-slate-300"
              }`}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background: on
                    ? SERIES_COLOURS[i % SERIES_COLOURS.length]
                    : "#475569",
                }}
              />
              {name}
            </button>
          );
        })}
      </div>

      {selected.length === 0 ? (
        <div className="mt-4">
          <Empty>Pick at least one measurement above to plot it.</Empty>
        </div>
      ) : (
        <div className="mt-5 h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.10)" vertical={false} />
              <XAxis
                dataKey="recorded_at"
                tickFormatter={(v) => formatDay(String(v))}
                stroke="#475569"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={28}
              />
              <YAxis
                stroke="#475569"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Tooltip
                contentStyle={{
                  background: "#0d1220",
                  border: "1px solid rgba(148,163,184,0.15)",
                  borderRadius: 10,
                  fontSize: 12,
                }}
                labelFormatter={(v) => formatDay(String(v))}
                labelStyle={{ color: "#94a3b8" }}
              />
              {selected.map((name) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={
                    SERIES_COLOURS[names.indexOf(name) % SERIES_COLOURS.length]
                  }
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {selected.length > 0 && (
        <ul className="mt-3 space-y-1">
          {selected
            .filter((n) => METRIC_GLOSS[n])
            .map((n) => (
              <li key={n} className="text-[11px] text-slate-600">
                <span className="font-mono text-slate-500">{n}</span> —{" "}
                {METRIC_GLOSS[n]}
              </li>
            ))}
        </ul>
      )}
    </section>
  );
}
