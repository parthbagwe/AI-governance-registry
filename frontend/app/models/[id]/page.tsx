"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { formatDate, RISK_META, STAGE_META, TYPE_LABEL } from "@/lib/display";
import type {
  ApprovalEvent,
  DataLineage,
  MLModel,
  ModelMetric,
} from "@/lib/types";
import { RiskBadge, StageBadge } from "@/components/Badges";
import { ErrorState, Loading } from "@/components/States";
import { Scorecard } from "@/components/Scorecard";
import { MetricChart } from "@/components/MetricChart";
import { AuditTrail } from "@/components/AuditTrail";
import { LineagePanel } from "@/components/LineagePanel";
import { ActionPanel } from "@/components/ActionPanel";
import { ExplainPanel } from "@/components/ExplainPanel";

export default function ModelDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [model, setModel] = useState<MLModel | null>(null);
  const [metrics, setMetrics] = useState<ModelMetric[]>([]);
  const [history, setHistory] = useState<ApprovalEvent[]>([]);
  const [lineage, setLineage] = useState<DataLineage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setRefreshing(true);
    try {
      const [m, mt, h, l] = await Promise.all([
        api.getModel(id),
        api.getMetrics(id),
        api.getHistory(id),
        api.getLineage(id),
      ]);
      setModel(m);
      setMetrics(mt);
      setHistory(h);
      setLineage(l);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // A stage change rewrites the audit trail, so refetch rather than patching
  // local state — the trail is the record, and it should never be guessed at.
  const handleChanged = useCallback(
    (updated: MLModel) => {
      setModel(updated);
      load();
    },
    [load]
  );

  if (error) return <ErrorState message={error} />;
  if (!model) return <Loading label="Loading model…" />;

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 transition hover:text-slate-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to portfolio
      </Link>

      <div className="panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-white">
                {model.name}
              </h1>
              <span className="font-mono text-sm text-slate-600">
                {model.version}
              </span>
            </div>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              {model.use_case}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StageBadge stage={model.stage} />
              <RiskBadge tier={model.risk_tier} />
              <span className="chip bg-white/[0.04] text-slate-400 ring-white/[0.07]">
                {TYPE_LABEL[model.model_type]}
              </span>
            </div>
          </div>

          <button
            onClick={load}
            disabled={refreshing}
            className="btn-ghost"
            aria-label="Refresh this model"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <dl className="mt-6 grid gap-4 border-t border-white/[0.06] pt-5 sm:grid-cols-2 lg:grid-cols-4">
          <Fact label="Owned by" value={model.owner} />
          <Fact label="Registered" value={formatDate(model.created_at)} />
          <Fact label="Last updated" value={formatDate(model.updated_at)} />
          <Fact
            label="Current status"
            value={STAGE_META[model.stage].plain}
          />
        </dl>

        <p className="mt-4 rounded-lg border border-white/[0.06] bg-ink-900/40 px-4 py-3 text-xs leading-relaxed text-slate-500">
          {RISK_META[model.risk_tier].plain}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Scorecard model={model} />
        <ActionPanel model={model} onChanged={handleChanged} />
      </div>

      <MetricChart metrics={metrics} />

      <div className="grid gap-6 lg:grid-cols-2">
        <AuditTrail events={history} />
        <LineagePanel lineage={lineage} />
      </div>

      {model.name === "sme-credit-scorer" && <ExplainPanel modelId={model.id} />}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="label">{label}</dt>
      <dd className="mt-1.5 text-sm text-slate-300">{value}</dd>
    </div>
  );
}
