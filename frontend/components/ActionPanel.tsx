"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, OctagonAlert, ShieldAlert, XCircle } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { STAGE_META } from "@/lib/display";
import {
  ALLOWED_TRANSITIONS,
  MIN_SCORE_BY_TIER,
  type MLModel,
  type ModelStage,
} from "@/lib/types";

type Outcome =
  | { kind: "success"; message: string }
  | { kind: "blocked"; status: number; message: string }
  | null;

/**
 * The interactive half of the page. Note what this component does *not* do:
 * it never decides whether an action is permitted. It can warn ahead of time
 * using a mirrored copy of the rules, but the API's answer is the only one
 * that counts — a blocked attempt renders the backend's own explanation
 * verbatim, which is exactly what makes the demo convincing.
 */
export function ActionPanel({
  model,
  onChanged,
}: {
  model: MLModel;
  onChanged: (updated: MLModel) => void;
}) {
  const legalStages = ALLOWED_TRANSITIONS[model.stage];

  const [target, setTarget] = useState<ModelStage | "">(legalStages[0] ?? "");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);

  // Reset the form whenever the model moves stage, so a stale target
  // (now illegal) can't sit selected after a successful transition.
  useEffect(() => {
    setTarget(ALLOWED_TRANSITIONS[model.stage][0] ?? "");
  }, [model.stage]);

  const required = MIN_SCORE_BY_TIER[model.risk_tier];
  const willLikelyFail =
    target === "production" &&
    (model.governance_score === null || model.governance_score < required);

  async function submit() {
    if (!target) return;
    setBusy(true);
    setOutcome(null);
    try {
      const updated = await api.approve(model.id, {
        to_stage: target,
        comment: comment.trim() || undefined,
      });
      onChanged(updated);
      setComment("");
      setOutcome({
        kind: "success",
        message: `Approved. This model is now "${STAGE_META[updated.stage].label}".`,
      });
    } catch (e) {
      if (e instanceof ApiError) {
        setOutcome({ kind: "blocked", status: e.status, message: e.message });
      } else {
        setOutcome({ kind: "blocked", status: 0, message: String(e) });
      }
    } finally {
      setBusy(false);
    }
  }

  if (model.stage === "deprecated") {
    return (
      <section className="panel p-5">
        <h2 className="text-sm font-semibold text-white">Governance actions</h2>
        <p className="mt-3 rounded-lg border border-white/[0.06] bg-ink-900/50 px-4 py-3 text-sm text-slate-400">
          This model is retired. Retirement is a terminal state — it can&apos;t
          be brought back. A replacement would be registered as a new version
          with its own approval history.
        </p>
      </section>
    );
  }

  return (
    <section className="panel p-5">
      <h2 className="text-sm font-semibold text-white">Governance actions</h2>
      <p className="mt-1 text-xs text-slate-500">
        Move this model to a different stage. Every action is recorded against
        your verified Supabase identity in the audit trail.
      </p>

      <div className="mt-5 space-y-4">
        <div>
          <label className="label mb-2 block">Move to</label>
          <div className="flex flex-wrap gap-2">
            {(["review", "production", "pilot", "deprecated"] as ModelStage[]).map(
              (s) => {
                const legal = legalStages.includes(s);
                const active = target === s;
                return (
                  <button
                    key={s}
                    disabled={!legal}
                    onClick={() => setTarget(s)}
                    title={
                      legal
                        ? STAGE_META[s].plain
                        : `Not a legal next step from "${STAGE_META[model.stage].label}"`
                    }
                    className={`rounded-lg border px-3 py-2 text-sm transition ${
                      active
                        ? "border-sky-400/40 bg-sky-400/10 text-sky-200"
                        : legal
                          ? "border-white/10 text-slate-300 hover:bg-white/5"
                          : "cursor-not-allowed border-white/[0.04] text-slate-700 line-through"
                    }`}
                  >
                    {STAGE_META[s].label}
                  </button>
                );
              }
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-600">
            Struck-through options aren&apos;t legal next steps from{" "}
            &ldquo;{STAGE_META[model.stage].label}&rdquo;. Stages can&apos;t be
            skipped.
          </p>
        </div>

        <div>
          <label className="label mb-2 block">Reason (optional)</label>
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Why are you making this change?"
            className="field"
          />
        </div>

        {willLikelyFail && (
          <div className="flex gap-3 rounded-lg border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
            <p className="text-xs leading-relaxed text-amber-200">
              Heads up: this model scores{" "}
              <b>{model.governance_score?.toFixed(2) ?? "nothing yet"}</b>, below
              the <b>{required.toFixed(1)}</b> required for a{" "}
              {model.risk_tier}-risk model. The backend will refuse this. Try it
              anyway if you want to see the gate fire.
            </p>
          </div>
        )}

        <button
          onClick={submit}
          disabled={busy || !target}
          className="btn-primary w-full sm:w-auto"
        >
          {busy ? "Submitting…" : "Submit for approval"}
        </button>

        {outcome && (
          <div
            className={`flex gap-3 rounded-lg border px-4 py-3 ${
              outcome.kind === "success"
                ? "border-emerald-400/20 bg-emerald-400/[0.06]"
                : "border-rose-400/20 bg-rose-400/[0.06]"
            }`}
          >
            {outcome.kind === "success" ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
            ) : (
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
            )}
            <div className="space-y-1">
              {outcome.kind === "blocked" && (
                <p className="text-xs font-semibold text-rose-200">
                  Blocked by the governance engine
                  {outcome.status ? ` (HTTP ${outcome.status})` : ""}
                </p>
              )}
              <p
                className={`text-xs leading-relaxed ${
                  outcome.kind === "success"
                    ? "text-emerald-200"
                    : "text-rose-200"
                }`}
              >
                {outcome.message}
              </p>
            </div>
          </div>
        )}
      </div>

      <KillSwitch model={model} onChanged={onChanged} />
    </section>
  );
}

/**
 * Deliberately its own control behind a disclosure, hitting its own endpoint.
 * RBI's draft guidance requires an override/suspension mechanism that works
 * regardless of a model's current stage — but an emergency stop should never
 * be one careless click away from the routine approval form.
 */
function KillSwitch({
  model,
  onChanged,
}: {
  model: MLModel;
  onChanged: (updated: MLModel) => void;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fire() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.killSwitch(model.id, reason.trim());
      onChanged(updated);
      setOpen(false);
      setReason("");
      setConfirmed(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 border-t border-white/[0.06] pt-5">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-2 text-xs font-medium text-rose-400 transition hover:text-rose-300"
        >
          <OctagonAlert className="h-4 w-4" />
          Emergency stop
        </button>
      ) : (
        <div className="rounded-lg border border-rose-400/25 bg-rose-500/[0.05] p-4">
          <div className="flex items-center gap-2">
            <OctagonAlert className="h-4 w-4 text-rose-400" />
            <h3 className="text-sm font-semibold text-rose-200">
              Emergency stop
            </h3>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            Immediately switches this model off, whatever stage it&apos;s in and
            whatever it scores. It skips the normal approval path entirely and
            is permanently flagged as an emergency in the audit trail. Retiring
            a model can&apos;t be undone.
          </p>

          <div className="mt-4 space-y-3">
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Documented reason (required — this can't be silent)"
              className="field"
            />
            <label className="flex items-start gap-2.5 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 rounded border-white/20 bg-transparent accent-rose-500"
              />
              I understand this immediately switches the model off and
              can&apos;t be reversed.
            </label>

            {error && (
              <p className="rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-3 py-2 text-xs text-rose-200">
                {error}
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              <button
                onClick={fire}
                disabled={busy || !confirmed || !reason.trim()}
                className="btn-danger"
              >
                {busy ? "Stopping…" : "Trigger emergency stop"}
              </button>
              <button
                onClick={() => {
                  setOpen(false);
                  setError(null);
                  setConfirmed(false);
                }}
                className="btn-ghost"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
