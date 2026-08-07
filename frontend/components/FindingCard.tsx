import { BookMarked, Wrench } from "lucide-react";

import { SEVERITY_META, type Finding } from "@/lib/assessment";

/**
 * One finding.
 *
 * The citation is not decoration. A tool that says "this is high risk" without
 * saying on whose authority is just an opinion with a colour attached — and an
 * opinion a reviewer can neither verify nor overturn. Naming the principle and
 * the paragraph means someone can go and read the source, and tell you you're
 * wrong. That possibility is the point.
 */
export function FindingCard({ finding }: { finding: Finding }) {
  const meta = SEVERITY_META[finding.severity];

  return (
    <div className="panel lift p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`chip ${meta.chip}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
          {meta.label}
        </span>
        <h3 className="text-sm font-medium text-white">{finding.title}</h3>
        {finding.evidence && (
          <span className="chip bg-white/[0.04] font-mono text-slate-400 ring-white/[0.07]">
            {finding.evidence}
          </span>
        )}
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-400">
        {finding.detail}
      </p>

      <div className="mt-3 flex items-start gap-2 rounded-lg border border-white/[0.06] bg-ink-900/40 px-3 py-2.5">
        <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-400" />
        <p className="text-xs leading-relaxed text-slate-300">{finding.action}</p>
      </div>

      <p className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-600">
        <BookMarked className="h-3 w-3" />
        <span className="text-slate-500">{finding.principle}</span>
        <span className="text-slate-700">·</span>
        <span className="font-mono">{finding.reference}</span>
      </p>
    </div>
  );
}
