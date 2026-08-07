"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Download, Search } from "lucide-react";

import { formatDate, METRIC_GLOSS } from "@/lib/display";
import { download, stampedName, toCsv } from "@/lib/export";
import type { ModelMetric } from "@/lib/types";
import { Empty } from "@/components/States";

/**
 * The raw log behind the chart.
 *
 * A chart is an interpretation — it smooths, it scales, it hides anything you
 * didn't select. For anyone actually checking the model's history, the
 * underlying rows matter: the exact value, the exact timestamp, and how many
 * measurements there really are. It's the difference between "the accuracy
 * dropped" and "here are the eleven readings that show it".
 *
 * Newest first by default, because the question is almost always "what
 * happened most recently".
 */
export function MetricsLog({
  metrics,
  modelName,
  modelVersion,
}: {
  metrics: ModelMetric[];
  modelName: string;
  modelVersion: string;
}) {
  const [query, setQuery] = useState("");
  const [metric, setMetric] = useState<string>("all");
  const [newestFirst, setNewestFirst] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const names = useMemo(
    () => Array.from(new Set(metrics.map((m) => m.metric_name))).sort(),
    [metrics]
  );

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = metrics.filter((m) => {
      if (metric !== "all" && m.metric_name !== metric) return false;
      if (!q) return true;
      return (
        m.metric_name.toLowerCase().includes(q) ||
        String(m.metric_value).includes(q) ||
        m.recorded_at.toLowerCase().includes(q)
      );
    });

    return filtered.sort((a, b) => {
      const d =
        new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime();
      return newestFirst ? -d : d;
    });
  }, [metrics, query, metric, newestFirst]);

  const shown = expanded ? rows : rows.slice(0, 12);

  function exportCsv() {
    download(
      stampedName(`metrics-${modelName}-${modelVersion}`, "csv"),
      toCsv(
        rows.map((m) => ({
          model_name: modelName,
          model_version: modelVersion,
          metric_name: m.metric_name,
          metric_value: m.metric_value,
          recorded_at: m.recorded_at,
        }))
      ),
      "text/csv;charset=utf-8"
    );
  }

  return (
    <section className="panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Measurement log</h2>
          <p className="mt-1 text-xs text-slate-500">
            Every reading behind the chart above — exact values and timestamps,
            as recorded.
          </p>
        </div>
        {metrics.length > 0 && (
          <button onClick={exportCsv} className="btn-ghost" title="Download as CSV">
            <Download className="h-4 w-4" />
            Export
          </button>
        )}
      </div>

      {metrics.length === 0 ? (
        <div className="mt-5">
          <Empty>
            Nothing logged for this model yet. Training and monitoring scripts
            write here as they run.
          </Empty>
        </div>
      ) : (
        <>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <div className="relative min-w-[180px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter readings…"
                className="field py-1.5 pl-8 text-xs"
              />
            </div>

            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="field w-auto py-1.5 text-xs"
            >
              <option value="all">All measurements</option>
              {names.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>

            <button
              onClick={() => setNewestFirst((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-400 transition hover:text-slate-200"
              title="Reverse the order"
            >
              {newestFirst ? (
                <ArrowDown className="h-3.5 w-3.5" />
              ) : (
                <ArrowUp className="h-3.5 w-3.5" />
              )}
              {newestFirst ? "Newest" : "Oldest"}
            </button>
          </div>

          <div className="mt-4 overflow-hidden rounded-lg border border-white/[0.06]">
            <div className="grid grid-cols-[minmax(0,1.6fr)_auto_minmax(0,1fr)] gap-3 border-b border-white/[0.06] bg-white/[0.02] px-4 py-2">
              <span className="label">Measurement</span>
              <span className="label text-right">Value</span>
              <span className="label text-right">Recorded</span>
            </div>

            <ul className="divide-y divide-white/[0.04]">
              {shown.map((m, i) => (
                <li
                  key={`${m.metric_name}-${m.recorded_at}-${i}`}
                  className="grid grid-cols-[minmax(0,1.6fr)_auto_minmax(0,1fr)] items-baseline gap-3 px-4 py-2.5 transition-colors hover:bg-white/[0.02]"
                >
                  <span
                    className="truncate font-mono text-xs text-slate-300"
                    title={METRIC_GLOSS[m.metric_name] ?? m.metric_name}
                  >
                    {m.metric_name}
                  </span>
                  <span className="text-right font-mono text-xs tabular-nums text-white">
                    {formatValue(m.metric_value)}
                  </span>
                  <span className="truncate text-right text-[11px] text-slate-500">
                    {formatDate(m.recorded_at)}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-[11px] text-slate-600">
              {rows.length} reading{rows.length === 1 ? "" : "s"}
              {rows.length !== metrics.length && ` of ${metrics.length}`}
            </p>
            {rows.length > 12 && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="text-xs text-sky-400 transition hover:text-sky-300"
              >
                {expanded ? "Show fewer" : `Show all ${rows.length}`}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}

/**
 * Metric values here span nine orders of magnitude — a drift share of 0.33
 * next to a price of 95.08 next to a sample size of 971. A single fixed
 * precision makes one of them unreadable, so the format follows the number.
 */
function formatValue(v: number): string {
  if (Number.isInteger(v) && Math.abs(v) >= 1000) return v.toLocaleString();
  if (Number.isInteger(v)) return String(v);
  if (Math.abs(v) >= 100) return v.toFixed(2);
  if (Math.abs(v) >= 1) return v.toFixed(4);
  return v.toFixed(4);
}
