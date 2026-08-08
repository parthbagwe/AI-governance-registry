"use client";

import { useMemo } from "react";

/**
 * A scrolling exchange ticker, of the kind that runs across the front of the
 * BSE building on Dalal Street.
 *
 * Two rows moving in opposite directions. That's the detail that sells it —
 * a single row scrolling one way reads as a marquee on a website, while
 * counter-moving rows read as a board, because a board has no single reading
 * direction.
 *
 * Values are generated per mount so no two loads show the same tape. They are
 * plainly synthetic and labelled as such; this is a loading visual, and
 * showing invented numbers styled as live quotes would be the wrong kind of
 * convincing.
 */

const SYMBOLS = [
  "RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK", "SBIN", "AXISBANK",
  "ITC", "BHARTIARTL", "KOTAKBANK", "LT", "HINDUNILVR", "SUNPHARMA",
  "MARUTI", "TITAN", "BAJFINANCE", "NTPC", "POWERGRID", "WIPRO", "NESTLEIND",
];

interface Quote {
  symbol: string;
  price: string;
  change: number;
}

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildQuotes(seed: number): Quote[] {
  const rand = mulberry32(seed);
  return SYMBOLS.map((symbol) => {
    // Prices span three orders of magnitude across a real index, so a single
    // range would make every row look identical.
    const magnitude = [1, 10, 100][Math.floor(rand() * 3)];
    const price = (120 + rand() * 2800) * (magnitude / 10);
    const change = (rand() - 0.46) * 4.2;
    return {
      symbol,
      price: price.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
      change: Number(change.toFixed(2)),
    };
  });
}

function Row({
  quotes,
  reverse,
  durationMs,
}: {
  quotes: Quote[];
  reverse: boolean;
  durationMs: number;
}) {
  // Rendered twice back to back. A single copy would leave a visible gap when
  // it wraps; two copies mean the second is already in place as the first
  // exits, so the loop has no seam.
  const doubled = [...quotes, ...quotes];

  return (
    <div className="relative overflow-hidden py-2">
      <div
        className="flex w-max items-center gap-8 whitespace-nowrap"
        style={{
          animation: `ticker-scroll ${durationMs}ms linear infinite`,
          animationDirection: reverse ? "reverse" : "normal",
        }}
      >
        {doubled.map((q, i) => {
          const up = q.change >= 0;
          return (
            <span key={`${q.symbol}-${i}`} className="flex items-baseline gap-2">
              <span className="font-mono text-[13px] font-medium tracking-wide text-slate-300">
                {q.symbol}
              </span>
              <span className="font-mono text-[13px] tabular-nums text-slate-500">
                {q.price}
              </span>
              <span
                className={`font-mono text-[13px] tabular-nums ${
                  up ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {up ? "+" : ""}
                {q.change.toFixed(2)}%
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export function TickerAnimation({
  seed,
  className = "",
}: {
  seed?: number;
  className?: string;
}) {
  const rows = useMemo(() => {
    const base = seed ?? Math.floor(Math.random() * 1_000_000);
    return [
      buildQuotes(base),
      buildQuotes(base + 7919), // a prime, so the two rows never correlate
      buildQuotes(base + 15733),
    ];
  }, [seed]);

  return (
    <div className={`w-full ${className}`}>
      <div className="relative overflow-hidden rounded-lg border border-white/[0.06] bg-black/40 py-1">
        {/* Faint scanlines — an LED board has visible structure, and without
            it this reads as a web marquee rather than as hardware. */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.18]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, rgba(255,255,255,0.09) 0px, rgba(255,255,255,0.09) 1px, transparent 1px, transparent 3px)",
          }}
        />

        <Row quotes={rows[0]} reverse={false} durationMs={22000} />
        <div className="h-px bg-white/[0.05]" />
        <Row quotes={rows[1]} reverse durationMs={26000} />
        <div className="h-px bg-white/[0.05]" />
        <Row quotes={rows[2]} reverse={false} durationMs={30000} />

        {/* Edges fade out, so rows appear to run past the board rather than
            starting and stopping at its borders. */}
        <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-ink-950 to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-ink-950 to-transparent" />
      </div>

      <p className="mt-3 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-slate-700">
        Illustrative values
      </p>
    </div>
  );
}
