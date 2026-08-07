import { Bot, OctagonAlert, User } from "lucide-react";

import { formatDate, STAGE_META } from "@/lib/display";
import type { ApprovalEvent } from "@/lib/types";
import { Empty } from "@/components/States";

/**
 * Append-only history of every stage change. This is the artefact an auditor
 * would actually ask for: who moved this model, when, and on what grounds —
 * including the automated actors, which are never hidden or relabelled as
 * human approvals.
 */
export function AuditTrail({ events }: { events: ApprovalEvent[] }) {
  return (
    <section className="panel p-5">
      <h2 className="text-sm font-semibold text-white">Audit trail</h2>
      <p className="mt-1 text-xs text-slate-500">
        Every stage change, in order. Nothing here is ever edited or deleted.
      </p>

      <div className="mt-5">
        {events.length === 0 ? (
          <Empty>No recorded events for this model.</Empty>
        ) : (
          <ol className="stagger relative space-y-5 border-l border-white/[0.08] pl-6">
            {events.map((e, i) => (
              <li key={i} className="relative">
                <span
                  className={`absolute -left-[27px] grid h-4 w-4 place-items-center rounded-full ring-4 ring-ink-950 ${
                    e.is_emergency ? "bg-rose-500" : STAGE_META[e.to_stage].dot
                  }`}
                />

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-500">
                    {e.from_stage
                      ? STAGE_META[e.from_stage].label
                      : "First registered"}
                  </span>
                  <span className="text-slate-700">→</span>
                  <span className="text-sm font-medium text-slate-200">
                    {STAGE_META[e.to_stage].label}
                  </span>
                  {e.is_emergency && (
                    <span className="chip bg-rose-500/10 text-rose-300 ring-rose-400/25">
                      <OctagonAlert className="h-3 w-3" />
                      Emergency stop
                    </span>
                  )}
                </div>

                <p className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
                  {isAutomated(e.approved_by) ? (
                    <Bot className="h-3 w-3 text-violet-400" />
                  ) : (
                    <User className="h-3 w-3 text-slate-600" />
                  )}
                  <span className="font-mono">{e.approved_by}</span>
                  <span className="text-slate-700">·</span>
                  {formatDate(e.created_at)}
                </p>

                {e.comment && (
                  <p className="mt-2 rounded-lg border border-white/[0.06] bg-ink-900/50 px-3 py-2 text-xs leading-relaxed text-slate-400">
                    {e.comment}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

/** Automated actors are marked visually so a robot approval never reads as human. */
function isAutomated(actor: string): boolean {
  return /(service|monitor|bot|job|pipeline)/i.test(actor);
}
