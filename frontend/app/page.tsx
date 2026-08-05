"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, Info, RefreshCw, Search } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { scoreHealth, TYPE_LABEL } from "@/lib/display";
import type { MLModel, ModelStage, RiskTier } from "@/lib/types";
import { RiskBadge, StageBadge } from "@/components/Badges";
import { PortfolioStats } from "@/components/PortfolioStats";
import { Empty, ErrorState, Loading } from "@/components/States";

type StageFilter = ModelStage | "all";
type RiskFilter = RiskTier | "all";

const STAGE_FILTERS: { value: StageFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "production", label: "Live" },
  { value: "review", label: "Under review" },
  { value: "pilot", label: "Testing" },
  { value: "deprecated", label: "Retired" },
];

const RISK_FILTERS: { value: RiskFilter; label: string }[] = [
  { value: "all", label: "Any risk" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function RegistryPage() {
  const [models, setModels] = useState<MLModel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<StageFilter>("all");
  const [risk, setRisk] = useState<RiskFilter>("all");

  async function load() {
    setRefreshing(true);
    try {
      setModels(await api.listModels());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    if (!models) return [];
    const q = query.trim().toLowerCase();
    return models.filter((m) => {
      if (stage !== "all" && m.stage !== stage) return false;
      if (risk !== "all" && m.risk_tier !== risk) return false;
      if (!q) return true;
      return (
        m.name.toLowerCase().includes(q) ||
        m.use_case.toLowerCase().includes(q) ||
        m.owner.toLowerCase().includes(q)
      );
    });
  }, [models, query, stage, risk]);

  if (error) return <ErrorState message={error} />;
  if (!models) return <Loading label="Loading the model registry…" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            Model portfolio
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Every AI model the bank runs, what stage it&apos;s at, and whether
            it has cleared the approval bar for the risk it carries.
          </p>
        </div>
        <button
          onClick={load}
          disabled={refreshing}
          className="btn-ghost"
          aria-label="Refresh the registry"
        >
          <RefreshCw
            className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>

      <PortfolioStats models={models} />

      <details className="panel group px-4 py-3 open:pb-4">
        <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-slate-300">
          <Info className="h-4 w-4 text-sky-400" />
          What am I looking at?
          <ChevronRight className="h-4 w-4 text-slate-600 transition group-open:rotate-90" />
        </summary>
        <div className="mt-3 space-y-2.5 text-sm leading-relaxed text-slate-400">
          <p>
            Banks now run dozens of AI models — credit scoring, fraud
            detection, chatbots. This registry is the layer above them: it
            records what exists, who signed it off, and whether it is still
            behaving the way it did when it was approved.
          </p>
          <p>
            A model moves through four stages — <b>Testing</b> →{" "}
            <b>Under Review</b> → <b>Live</b> → <b>Retired</b>. It cannot skip
            ahead, and it cannot go live until it scores well enough on five
            dimensions. The higher the risk it carries, the higher that bar
            gets: a credit model that moves customers&apos; money is held to a
            stricter standard than an internal FAQ bot.
          </p>
          <p>
            Every one of those rules is enforced in the backend, not in this
            page. This page only shows you what the API decided.
          </p>
        </div>
      </details>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, use case, or owning team…"
            className="field pl-9"
          />
        </div>

        <FilterGroup
          options={STAGE_FILTERS}
          value={stage}
          onChange={(v) => setStage(v as StageFilter)}
        />
        <FilterGroup
          options={RISK_FILTERS}
          value={risk}
          onChange={(v) => setRisk(v as RiskFilter)}
        />
      </div>

      {filtered.length === 0 ? (
        <Empty>
          No models match those filters.{" "}
          {models.length === 0 && (
            <>
              The registry is empty — run <code>python seed.py</code> to load
              the sample portfolio.
            </>
          )}
        </Empty>
      ) : (
        <div className="panel overflow-hidden">
          {/* Table on desktop, stacked cards on mobile — same data, no truncation. */}
          <div className="hidden grid-cols-[minmax(0,2.4fr)_auto_auto_auto_auto] items-center gap-4 border-b border-white/[0.06] px-5 py-3 md:grid">
            <span className="label">Model</span>
            <span className="label">Stage</span>
            <span className="label">Risk tier</span>
            <span className="label text-right">Score</span>
            <span className="sr-only">Open</span>
          </div>

          <ul className="divide-y divide-white/[0.05]">
            {filtered.map((m) => (
              <li key={m.id}>
                <ModelRow model={m} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function FilterGroup({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-lg border border-white/10 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition ${
            value === o.value
              ? "bg-white/10 text-white"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ModelRow({ model }: { model: MLModel }) {
  const health = scoreHealth(model.governance_score);

  return (
    <Link
      href={`/models/${model.id}`}
      className="grid grid-cols-1 gap-3 px-5 py-4 transition hover:bg-white/[0.03] md:grid-cols-[minmax(0,2.4fr)_auto_auto_auto_auto] md:items-center md:gap-4"
    >
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-medium text-white">{model.name}</span>
          <span className="shrink-0 font-mono text-[11px] text-slate-600">
            {model.version}
          </span>
        </div>
        <p className="mt-0.5 truncate text-sm text-slate-500">
          {model.use_case}
        </p>
        <p className="mt-1 text-[11px] text-slate-600">
          {TYPE_LABEL[model.model_type]} · owned by {model.owner}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 md:contents">
        <StageBadge stage={model.stage} />
        <RiskBadge tier={model.risk_tier} />

        <div className="md:text-right">
          <span
            className={`font-mono text-sm font-semibold tabular-nums ${health.tone}`}
          >
            {model.governance_score?.toFixed(2) ?? "—"}
          </span>
          <span className="ml-2 text-[11px] text-slate-600 md:ml-0 md:block">
            {health.label}
          </span>
        </div>
      </div>

      <ChevronRight className="hidden h-4 w-4 text-slate-700 md:block" />
    </Link>
  );
}
