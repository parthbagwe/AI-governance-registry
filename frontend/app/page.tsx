"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, Info, RefreshCw, Search } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { scoreHealth, TYPE_LABEL } from "@/lib/display";
import { isLiveSource, type MLModel, type ModelStage, type RiskTier } from "@/lib/types";
import { LiveBadge, RiskBadge, StageBadge } from "@/components/Badges";
import { PortfolioStats } from "@/components/PortfolioStats";
import { TextReveal } from "@/components/TextReveal";
import { StatsSkeleton, TableSkeleton } from "@/components/Skeleton";
import { LineageExport } from "@/components/LineageExport";
import { useMinDuration } from "@/lib/useMinDuration";
import { Empty, ErrorState } from "@/components/States";

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

const SOURCE_FILTERS: { value: "all" | "live"; label: string }[] = [
  { value: "all", label: "All sources" },
  { value: "live", label: "Live feeds" },
];

export default function RegistryPage() {
  const [models, setModels] = useState<MLModel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<StageFilter>("all");
  const [risk, setRisk] = useState<RiskFilter>("all");
  const [source, setSource] = useState<"all" | "live">("all");

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
      if (source === "live" && !isLiveSource(m)) return false;
      if (!q) return true;
      return (
        m.name.toLowerCase().includes(q) ||
        m.use_case.toLowerCase().includes(q) ||
        m.owner.toLowerCase().includes(q)
      );
    });
  }, [models, query, stage, risk, source]);

  // The masthead renders immediately and the data slots in underneath, rather
  // than the whole page being replaced by a spinner. There's nothing you need
  // to wait for in order to know what this page is.
  //
  // The floor stops the skeleton flashing on a fast local API — below about
  // 400ms a loading state that appears and vanishes reads as a glitch.
  const pending = useMinDuration(models === null, 500);

  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      {/* Masthead. Deliberately larger than a dashboard heading needs to be —
          it gives the word-by-word reveal something to work with, and it sets
          the tone before any data loads. */}
      <section className="pb-2 pt-6 sm:pt-10">
        <p
          className="fade-in label mb-5 text-slate-500"
          style={{ animationDelay: "0.15s" }}
        >
          Model risk management
        </p>

        <TextReveal
          as="h1"
          text="Every model the bank runs, and whether it has earned the right to run."
          className="max-w-4xl text-[clamp(1.9rem,5.2vw,3.4rem)] font-semibold leading-[1.08] tracking-[-0.02em] text-white"
          delay={120}
        />

        <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
          <TextReveal
            text="Approval is a statement about the world at a point in time. This is what watches for the world changing."
            className="max-w-xl text-sm leading-relaxed text-slate-400"
            delay={620}
            stagger={14}
          />
          <div
            className="fade-in flex flex-wrap items-center gap-2"
            style={{ animationDelay: "1s" }}
          >
            <LineageExport />
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
        </div>

        <div className="rule mt-8" style={{ animationDelay: "0.5s" }} />
      </section>

      {/* Null-checked inline as well as via the timing floor, so TypeScript
          narrows the type and PortfolioStats never sees a nullable prop. */}
      {pending || models === null ? (
        <StatsSkeleton />
      ) : (
        <PortfolioStats models={models} />
      )}

      <details className="panel group rise px-4 py-3 open:pb-4" style={{ animationDelay: "0.3s" }}>
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
        <FilterGroup
          options={SOURCE_FILTERS}
          value={source}
          onChange={(v) => setSource(v as "all" | "live")}
        />
      </div>

      {pending || models === null ? (
        <TableSkeleton />
      ) : filtered.length === 0 ? (
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
        <div className="panel rise overflow-hidden" style={{ animationDelay: "0.4s" }}>
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
      className="group/row grid grid-cols-1 gap-3 px-5 py-4 transition-colors duration-300 hover:bg-white/[0.035] md:grid-cols-[minmax(0,2.4fr)_auto_auto_auto_auto] md:items-center md:gap-4"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="truncate font-medium text-white">{model.name}</span>
          <span className="shrink-0 font-mono text-[11px] text-slate-600">
            {model.version}
          </span>
          {isLiveSource(model) && <LiveBadge className="shrink-0" />}
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

      {/* Nudges right on hover — the only bit of pure decoration here, and it
          earns its place by signalling the row is clickable. */}
      <ChevronRight className="hidden h-4 w-4 text-slate-700 transition-transform duration-300 group-hover/row:translate-x-1 group-hover/row:text-slate-400 md:block" />
    </Link>
  );
}
