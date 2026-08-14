/**
 * Thin client over the FastAPI governance API.
 *
 * Deliberately dumb: it holds zero governance logic. Whether a transition is
 * legal, whether a score clears the bar, whether a kill switch is permitted —
 * all of that is decided server-side in app/workflow.py. This file's only job
 * is to carry the question there and bring the answer back, including the
 * error message verbatim when the API says no.
 */

import type {
  MLModel,
  ModelMetric,
  ApprovalEvent,
  DataLineage,
  LineageExportRow,
  ModelStage,
  ExplainResult,
  ModelForecast,
} from "./types";
import { createClient } from "./supabase/client";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Thrown for any non-2xx response, carrying the API's own explanation. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Adds the current Supabase access token to any request sent to FastAPI. */
export async function authenticatedFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const {
    data: { session },
  } = await createClient().auth.getSession();
  const headers = new Headers(init?.headers);
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  return fetch(input, { ...init, headers });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    res = await authenticatedFetch(`${API_BASE}${path}`, {
      ...init,
      cache: "no-store",
      headers,
    });
  } catch {
    throw new ApiError(
      0,
      `Could not reach the API at ${API_BASE}. Is the FastAPI server running?`
    );
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = JSON.stringify(body.detail);
    } catch {
      /* response had no JSON body — keep the generic message */
    }
    if (res.status === 401 && typeof window !== "undefined") {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.assign(`/login?next=${encodeURIComponent(next)}`);
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  listModels: () => request<MLModel[]>("/models"),

  getModel: (id: string) => request<MLModel>(`/models/${id}`),

  getMetrics: (id: string, metricName?: string) =>
    request<ModelMetric[]>(
      `/models/${id}/metrics${
        metricName ? `?metric_name=${encodeURIComponent(metricName)}` : ""
      }`
    ),

  getForecast: (id: string, horizonDays = 30) =>
    request<ModelForecast>(`/models/${id}/forecast?horizon_days=${horizonDays}`),

  getHistory: (id: string) => request<ApprovalEvent[]>(`/models/${id}/history`),

  getLineage: (id: string) => request<DataLineage[]>(`/models/${id}/lineage`),

  /** Every data source across every model version — one row per pairing. */
  exportLineage: () => request<LineageExportRow[]>("/lineage"),

  approve: (
    id: string,
    body: { to_stage: ModelStage; comment?: string }
  ) =>
    request<MLModel>(`/models/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** The actor is derived by FastAPI from the verified Supabase token. */
  killSwitch: (id: string, reason: string) =>
    request<MLModel>(
      `/models/${id}/kill-switch?reason=${encodeURIComponent(reason)}`,
      { method: "POST" }
    ),

  explain: (id: string, applicant: Record<string, number>) =>
    request<ExplainResult>(`/models/${id}/explain`, {
      method: "POST",
      body: JSON.stringify(applicant),
    }),
};
