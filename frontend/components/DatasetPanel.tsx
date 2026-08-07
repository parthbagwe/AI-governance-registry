"use client";

import { useEffect, useState } from "react";
import { Download, FlaskConical, Globe, Lock, Table2 } from "lucide-react";

import { API_BASE } from "@/lib/api";
import { humaniseField } from "@/lib/display";

/**
 * Lets a reviewer actually look at the data behind a model.
 *
 * A lineage record saying "trained on gst_returns" is a claim. Being able to
 * open a hundred rows of it is closer to evidence, and it's the difference
 * between a register you read and one you can check.
 *
 * Not every model offers this, and the panel says so plainly when it doesn't.
 * A refusal here isn't a gap to apologise for — it's the correct answer for
 * anything trained on customer records, and worth showing as such.
 */

interface DatasetInfo {
  available: boolean;
  reason?: "not_exposed" | "file_missing";
  filename?: string;
  label?: string;
  provenance?: "synthetic" | "real_public";
  provenance_label?: string;
  description?: string;
  total_rows?: number;
  columns?: string[];
  sample_rows?: number;
  capped?: boolean;
  preview?: Record<string, number | string | null>[];
}

export function DatasetPanel({ modelId }: { modelId: string }) {
  const [info, setInfo] = useState<DatasetInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/models/${modelId}/dataset/info`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => !cancelled && setInfo(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [modelId]);

  // Silently absent rather than showing an empty box — a panel that only ever
  // says "nothing here" is noise on nine pages out of ten.
  if (failed) return null;
  if (!info) return null;

  if (!info.available) {
    if (info.reason === "not_exposed") {
      return (
        <section className="panel p-5">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.04] ring-1 ring-inset ring-white/[0.07]">
              <Lock className="h-4 w-4 text-slate-500" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-white">
                Dataset not exposed
              </h2>
              <p className="mt-1.5 max-w-xl text-xs leading-relaxed text-slate-500">
                No sample is available for this model. Datasets are opt-in and
                only qualify if they&apos;re synthetic or already public — a
                model trained on customer records is never readable through
                this API, however convenient that would be for a reviewer.
              </p>
            </div>
          </div>
        </section>
      );
    }

    return (
      <section className="panel p-5">
        <h2 className="text-sm font-semibold text-white">Dataset</h2>
        <p className="mt-1.5 max-w-xl text-xs leading-relaxed text-slate-500">
          <code className="font-mono text-slate-400">{info.filename}</code> isn&apos;t
          present on this instance. Datasets are generated locally and not
          committed, so a deployed instance won&apos;t have them unless they
          were shipped with it.
        </p>
      </section>
    );
  }

  const isSynthetic = info.provenance === "synthetic";
  const columns = info.columns ?? [];
  const preview = info.preview ?? [];

  return (
    <section className="panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-sky-400/10 ring-1 ring-inset ring-sky-400/25">
            <Table2 className="h-4 w-4 text-sky-300" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-white">{info.label}</h2>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <span
                className={`chip ${
                  isSynthetic
                    ? "bg-amber-400/10 text-amber-300 ring-amber-400/25"
                    : "bg-emerald-400/10 text-emerald-300 ring-emerald-400/25"
                }`}
              >
                {isSynthetic ? (
                  <FlaskConical className="h-3 w-3" />
                ) : (
                  <Globe className="h-3 w-3" />
                )}
                {info.provenance_label}
              </span>
              <span className="font-mono text-[11px] text-slate-600">
                {info.filename}
              </span>
              <span className="text-[11px] text-slate-600">
                {info.total_rows?.toLocaleString()} rows × {columns.length} columns
              </span>
            </div>
          </div>
        </div>

        <a
          href={`${API_BASE}/models/${modelId}/dataset`}
          className="btn-ghost"
          title="Downloads a CSV — opens directly in Excel"
        >
          <Download className="h-4 w-4" />
          Download sample
        </a>
      </div>

      <p className="mt-4 max-w-2xl text-xs leading-relaxed text-slate-500">
        {info.description}
      </p>

      {preview.length > 0 && (
        <div className="mt-5 overflow-x-auto rounded-lg border border-white/[0.06]">
          <table className="w-full min-w-[560px] border-collapse text-left">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                {columns.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2">
                    <span className="label" title={c}>
                      {humaniseField(c)}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-white/[0.03] transition-colors last:border-0 hover:bg-white/[0.02]"
                >
                  {columns.map((c) => (
                    <td
                      key={c}
                      className="whitespace-nowrap px-3 py-2 font-mono text-[11px] tabular-nums text-slate-400"
                    >
                      {formatCell(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 text-[11px] text-slate-600">
        Showing the first {preview.length} rows.{" "}
        {info.capped ? (
          <>
            The download is capped at {info.sample_rows?.toLocaleString()} of{" "}
            {info.total_rows?.toLocaleString()} rows — a register exists to
            describe data, not to become a second copy of it.
          </>
        ) : (
          <>The download contains all {info.total_rows?.toLocaleString()} rows.</>
        )}
      </p>
    </section>
  );
}

function formatCell(v: number | string | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString();
    return Math.abs(v) >= 1000 ? v.toLocaleString() : String(v);
  }
  return String(v);
}
