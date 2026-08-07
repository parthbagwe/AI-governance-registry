"use client";

import { useState } from "react";
import { Check, Download, FileJson, FileSpreadsheet } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { download, stampedName, toCsv } from "@/lib/export";

/**
 * Exports the whole portfolio's data lineage.
 *
 * The question this answers isn't "what does this model use" — the detail page
 * already covers that. It's the reverse: *this source table turned out to be
 * wrong, which models are affected?* That's the query a data steward runs the
 * morning after a bad upstream load, and answering it by clicking through ten
 * models is exactly the manual work a lineage register is supposed to remove.
 *
 * CSV by default because the recipient is usually opening a spreadsheet. JSON
 * offered alongside for anyone piping it somewhere.
 */
export function LineageExport() {
  const [busy, setBusy] = useState<null | "csv" | "json">(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(format: "csv" | "json") {
    setBusy(format);
    setError(null);
    try {
      const rows = await api.exportLineage();

      if (rows.length === 0) {
        setError("No lineage recorded yet for any model.");
        return;
      }

      if (format === "csv") {
        // Explicit column order: identity first, then the data, then the
        // prose. Whoever opens this should be able to read left to right and
        // have it make sense without rearranging anything.
        const csv = toCsv(rows, [
          "model_name",
          "model_version",
          "stage",
          "risk_tier",
          "owner",
          "source_table",
          "features_used",
          "notes",
          "model_id",
        ]);
        download(stampedName("governance-lineage", "csv"), csv, "text/csv;charset=utf-8");
      } else {
        download(
          stampedName("governance-lineage", "json"),
          JSON.stringify(rows, null, 2),
          "application/json"
        );
      }

      setDone(true);
      setTimeout(() => setDone(false), 2200);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => run("csv")}
          disabled={busy !== null}
          className="btn-ghost"
          title="One row per model version and data source, for a spreadsheet"
        >
          {done ? (
            <Check className="h-4 w-4 text-emerald-400" />
          ) : (
            <FileSpreadsheet className="h-4 w-4" />
          )}
          {busy === "csv" ? "Preparing…" : done ? "Downloaded" : "Export lineage (CSV)"}
        </button>

        <button
          onClick={() => run("json")}
          disabled={busy !== null}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs text-slate-500 transition hover:text-slate-300"
          title="Same data as JSON"
        >
          <FileJson className="h-3.5 w-3.5" />
          JSON
        </button>
      </div>

      {error && (
        <p className="rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-3 py-2 text-xs text-rose-200">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * Compact single-model variant, for the detail page's lineage panel.
 */
export function ModelLineageExport({
  modelName,
  modelVersion,
  modelId,
}: {
  modelName: string;
  modelVersion: string;
  modelId: string;
}) {
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const rows = await api.getLineage(modelId);
      if (rows.length === 0) return;

      // Re-attached here rather than exported bare: a lineage file that
      // doesn't say which model it describes is useless the moment it leaves
      // the browser's downloads folder.
      const enriched = rows.map((r) => ({
        model_name: modelName,
        model_version: modelVersion,
        source_table: r.source_table,
        features_used: r.features_used,
        notes: r.notes,
      }));

      download(
        stampedName(`lineage-${modelName}-${modelVersion}`, "csv"),
        toCsv(enriched),
        "text/csv;charset=utf-8"
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={run}
      disabled={busy}
      className="inline-flex items-center gap-1.5 text-xs text-slate-500 transition hover:text-slate-300"
      title="Download this model's data sources as CSV"
    >
      <Download className="h-3.5 w-3.5" />
      {busy ? "Preparing…" : "Export"}
    </button>
  );
}
