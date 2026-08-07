/**
 * Client-side file export.
 *
 * Done in the browser rather than server-side because the data is already
 * here — round-tripping it back to the API just to be handed the same rows as
 * a file would be slower and would need a second endpoint doing the same work.
 */

/**
 * Escapes one CSV field.
 *
 * This is the part everyone skips and then regrets. The lineage notes contain
 * commas, quotes and newlines — a naive `values.join(",")` produces a file
 * that opens in Excel with columns silently shifted, which is worse than a
 * file that fails loudly. RFC 4180: wrap in quotes, and double any quote
 * inside.
 */
function csvField(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = Array.isArray(value) ? value.join("; ") : String(value);
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export function toCsv(rows: Record<string, unknown>[], columns?: string[]): string {
  if (rows.length === 0) return "";
  const cols = columns ?? Object.keys(rows[0]);
  const header = cols.map(csvField).join(",");
  const body = rows.map((r) => cols.map((c) => csvField(r[c])).join(",")).join("\r\n");
  // CRLF and a UTF-8 BOM: without the BOM, Excel on Windows renders anything
  // non-ASCII as mojibake, and the notes fields contain em-dashes.
  return `﻿${header}\r\n${body}`;
}

export function download(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoked on the next tick — revoking synchronously can cancel the download
  // in some browsers before it has started reading the blob.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** `governance-lineage-2026-08-07.csv` — sorts chronologically in a folder. */
export function stampedName(base: string, ext: string): string {
  const d = new Date();
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
  return `${base}-${iso}.${ext}`;
}
