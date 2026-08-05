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
  ModelStage,
  ExplainResult,
} from "./types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
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

  getHistory: (id: string) => request<ApprovalEvent[]>(`/models/${id}/history`),

  getLineage: (id: string) => request<DataLineage[]>(`/models/${id}/lineage`),

  approve: (
    id: string,
    body: { to_stage: ModelStage; approved_by: string; comment?: string }
  ) =>
    request<MLModel>(`/models/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /**
   * NOTE: the kill-switch route declares `reason` and `triggered_by` as bare
   * function arguments in routes.py, which FastAPI interprets as *query
   * parameters*, not a JSON body. Sending them as a body returns a 422.
   */
  killSwitch: (id: string, reason: string, triggeredBy: string) =>
    request<MLModel>(
      `/models/${id}/kill-switch?reason=${encodeURIComponent(
        reason
      )}&triggered_by=${encodeURIComponent(triggeredBy)}`,
      { method: "POST" }
    ),

  explain: (id: string, applicant: Record<string, number>) =>
    request<ExplainResult>(`/models/${id}/explain`, {
      method: "POST",
      body: JSON.stringify(applicant),
    }),
};
