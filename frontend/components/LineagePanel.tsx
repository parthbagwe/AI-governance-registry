import { Database } from "lucide-react";

import type { DataLineage } from "@/lib/types";
import { humaniseField } from "@/lib/display";
import { Empty } from "@/components/States";

/**
 * Answers "what data feeds this model" from the registry itself rather than
 * from someone's memory or a stale wiki page — which is what makes the
 * reverse question tractable: if a source table turns out to be wrong, which
 * models need re-review?
 */
export function LineagePanel({ lineage }: { lineage: DataLineage[] }) {
  return (
    <section className="panel p-5">
      <h2 className="text-sm font-semibold text-white">Data lineage</h2>
      <p className="mt-1 text-xs text-slate-500">
        The sources and fields this model version was built on.
      </p>

      <div className="mt-5 space-y-3">
        {lineage.length === 0 ? (
          <Empty>No lineage recorded for this model.</Empty>
        ) : (
          lineage.map((l, i) => (
            <div
              key={i}
              className="rounded-lg border border-white/[0.06] bg-ink-900/40 p-4"
            >
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-sky-400" />
                <span className="font-mono text-sm text-slate-200">
                  {l.source_table}
                </span>
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
          ))
        )}
      </div>
    </section>
  );
}
