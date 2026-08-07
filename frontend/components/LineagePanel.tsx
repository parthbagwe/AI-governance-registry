import { Database, Radio } from "lucide-react";

import type { DataLineage } from "@/lib/types";
import { humaniseField } from "@/lib/display";
import { Empty } from "@/components/States";

/**
 * Answers "what data feeds this model" from the registry itself rather than
 * from someone's memory or a stale wiki page — which is what makes the
 * reverse question tractable: if a source table turns out to be wrong, which
 * models need re-review?
 */
export function LineagePanel({
  lineage,
  action,
}: {
  lineage: DataLineage[];
  action?: React.ReactNode;
}) {
  return (
    <section className="panel p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Data lineage</h2>
          <p className="mt-1 text-xs text-slate-500">
            The sources and fields this model version was built on.
          </p>
        </div>
        {action}
      </div>

      <div className="mt-5 space-y-3">
        {lineage.length === 0 ? (
          <Empty>No lineage recorded for this model.</Empty>
        ) : (
          lineage.map((l, i) => {
            // Sources registered as "live: <url>" are fetched at monitoring
            // time rather than read from a stored file — worth marking, since
            // "is this data still arriving?" is the first question anyone
            // reviewing a monitoring model asks.
            const isLive = l.source_table.startsWith("live:");
            return (
            <div
              key={i}
              className={`rounded-lg border p-4 ${
                isLive
                  ? "border-emerald-400/20 bg-emerald-400/[0.04]"
                  : "border-white/[0.06] bg-ink-900/40"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                {isLive ? (
                  <Radio className="h-4 w-4 shrink-0 text-emerald-400" />
                ) : (
                  <Database className="h-4 w-4 shrink-0 text-sky-400" />
                )}
                <span className="break-all font-mono text-sm text-slate-200">
                  {isLive ? l.source_table.slice(5).trim() : l.source_table}
                </span>
                {isLive && (
                  <span className="chip bg-emerald-400/10 text-emerald-300 ring-emerald-400/25">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    </span>
                    Live feed
                  </span>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {l.features_used.map((f) => (
                  <span
                    key={f}
                    className="chip bg-white/[0.04] text-slate-400 ring-white/[0.07]"
                    title={f}
                  >
                    {humaniseField(f)}
                  </span>
                ))}
              </div>

              {l.notes && (
                <p className="mt-3 text-xs leading-relaxed text-slate-500">
                  {l.notes}
                </p>
              )}
            </div>
            );
          })
        )}
      </div>
    </section>
  );
}
