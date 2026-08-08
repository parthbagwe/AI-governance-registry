"use client";

import { useMemo } from "react";

/**
 * An animated candlestick chart, used as the loading and transition visual.
 *
 * Chosen because it isn't decoration here — this project monitors FX markets,
 * so the loading state shows the thing the system actually watches. A generic
 * spinner would say nothing; a price series says "market data is being read".
 *
 * The series is a seeded random walk regenerated on each mount, so every
 * transition shows a different chart. A fixed one would start to feel like a
 * static image after the third navigation.
 *
 * Candles grow from their own midpoint outward in sequence, which is what
 * makes it read as a chart *forming* rather than a picture fading in. The
 * moving-average line draws left to right behind them at a slightly slower
 * rate, so the two layers don't move as one.
 */

const CANDLES = 26;
const WIDTH = 760;
const HEIGHT = 300;
const PADDING = { top: 22, right: 74, bottom: 22, left: 14 };

/** Deterministic PRNG — same seed, same chart. Small and dependency-free. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Candle {
  open: number;
  close: number;
  high: number;
  low: number;
}

function buildSeries(seed: number): Candle[] {
  const rand = mulberry32(seed);
  const out: Candle[] = [];

  let price = 100;
  // Mild upward drift with real pullbacks — a pure random walk tends to look
  // either flat or absurd, and a monotonic rise looks fake.
  for (let i = 0; i < CANDLES; i++) {
    const drift = 0.42;
    const volatility = 2.6 + rand() * 1.6;
    const move = (rand() - 0.5) * volatility * 2 + drift;

    const open = price;
    const close = open + move;
    const wickUp = rand() * volatility * 0.7;
    const wickDown = rand() * volatility * 0.7;

    out.push({
      open,
      close,
      high: Math.max(open, close) + wickUp,
      low: Math.min(open, close) - wickDown,
    });

    price = close;
  }

  return out;
}

export function CandlestickAnimation({
  className = "",
  seed,
  candleMs = 260,
  staggerMs = 34,
}: {
  className?: string;
  seed?: number;
  candleMs?: number;
  staggerMs?: number;
}) {
  const { candles, scaleY, slotWidth, maPath, gridLines } = useMemo(() => {
    const s = seed ?? Math.floor(Math.random() * 1_000_000);
    const data = buildSeries(s);

    const highs = data.map((c) => c.high);
    const lows = data.map((c) => c.low);
    const max = Math.max(...highs);
    const min = Math.min(...lows);
    const range = max - min || 1;

    const plotH = HEIGHT - PADDING.top - PADDING.bottom;
    const plotW = WIDTH - PADDING.left - PADDING.right;

    const y = (v: number) => PADDING.top + ((max - v) / range) * plotH;
    const slot = plotW / CANDLES;

    // 5-period moving average, drawn behind the candles.
    const points: string[] = [];
    for (let i = 0; i < data.length; i++) {
      const window = data.slice(Math.max(0, i - 4), i + 1);
      const avg = window.reduce((a, c) => a + c.close, 0) / window.length;
      points.push(`${PADDING.left + slot * i + slot / 2},${y(avg).toFixed(2)}`);
    }

    // Price gridlines at even intervals, labelled — the labels are what make it
    // read as a trading screen rather than an abstract bar chart.
    const lines = Array.from({ length: 5 }).map((_, i) => {
      const value = min + (range / 4) * i;
      return { y: y(value), label: value.toFixed(3) };
    });

    return {
      candles: data,
      scaleY: y,
      slotWidth: slot,
      maPath: `M${points.join("L")}`,
      gridLines: lines,
    };
  }, [seed]);

  const total = candleMs + staggerMs * (CANDLES - 1);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className={`w-full ${className}`}
      aria-hidden="true"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Grid */}
      <g>
        {gridLines.map((line, i) => (
          <g key={i}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={line.y}
              y2={line.y}
              stroke="rgba(148,163,184,0.09)"
              strokeWidth={1}
            />
            <text
              x={WIDTH - PADDING.right + 10}
              y={line.y + 3.5}
              fill="rgba(148,163,184,0.32)"
              fontSize={9}
              fontFamily="ui-monospace, monospace"
            >
              {line.label}
            </text>
          </g>
        ))}
        {Array.from({ length: 7 }).map((_, i) => {
          const x =
            PADDING.left + ((WIDTH - PADDING.left - PADDING.right) / 6) * i;
          return (
            <line
              key={`v${i}`}
              x1={x}
              x2={x}
              y1={PADDING.top - 12}
              y2={HEIGHT - PADDING.bottom + 12}
              stroke="rgba(148,163,184,0.05)"
              strokeWidth={1}
            />
          );
        })}
      </g>

      {/* Moving average, drawn with a dash offset so it writes itself in.
          Slightly slower than the candles so the layers stay distinguishable. */}
      <path
        d={maPath}
        fill="none"
        stroke="rgba(148,163,184,0.38)"
        strokeWidth={1.4}
        strokeLinecap="round"
        style={{
          strokeDasharray: 1400,
          animation: `draw ${total + 260}ms cubic-bezier(0.16, 1, 0.3, 1) both`,
          ["--dash" as string]: "1400",
        }}
      />

      {/* Candles */}
      {candles.map((c, i) => {
        const up = c.close >= c.open;
        const colour = up ? "#34d399" : "#f87171";
        const cx = PADDING.left + slotWidth * i + slotWidth / 2;
        const bodyW = Math.max(slotWidth * 0.58, 2);

        const bodyTop = scaleY(Math.max(c.open, c.close));
        const bodyBottom = scaleY(Math.min(c.open, c.close));
        const bodyH = Math.max(bodyBottom - bodyTop, 1.5);
        const midY = bodyTop + bodyH / 2;

        return (
          <g
            key={i}
            style={{
              // Grows outward from its own midpoint. Scaling from the baseline
              // would make the whole series look like it's being poured in;
              // from the middle it reads as each bar resolving in place.
              transformOrigin: `${cx}px ${midY}px`,
              animation: `candle-in ${candleMs}ms cubic-bezier(0.16, 1, 0.3, 1) both`,
              animationDelay: `${i * staggerMs}ms`,
            }}
          >
            <line
              x1={cx}
              x2={cx}
              y1={scaleY(c.high)}
              y2={scaleY(c.low)}
              stroke={colour}
              strokeWidth={1}
              opacity={0.85}
            />
            <rect
              x={cx - bodyW / 2}
              y={bodyTop}
              width={bodyW}
              height={bodyH}
              fill={colour}
              rx={0.6}
            />
          </g>
        );
      })}

      {/* Last-price marker — the detail that makes it look live rather than
          historical. Pulses on the final candle only. */}
      {candles.length > 0 &&
        (() => {
          const last = candles[candles.length - 1];
          const y = scaleY(last.close);
          const up = last.close >= last.open;
          const colour = up ? "#34d399" : "#f87171";
          return (
            <g
              style={{
                animation: `fade 400ms ease-out both`,
                animationDelay: `${total}ms`,
              }}
            >
              <line
                x1={PADDING.left}
                x2={WIDTH - PADDING.right}
                y1={y}
                y2={y}
                stroke={colour}
                strokeWidth={0.8}
                strokeDasharray="3 4"
                opacity={0.45}
              />
              <rect
                x={WIDTH - PADDING.right + 4}
                y={y - 8}
                width={62}
                height={16}
                rx={3}
                fill={colour}
                opacity={0.16}
              />
              <text
                x={WIDTH - PADDING.right + 10}
                y={y + 3.5}
                fill={colour}
                fontSize={9.5}
                fontFamily="ui-monospace, monospace"
              >
                {last.close.toFixed(3)}
              </text>
            </g>
          );
        })()}
    </svg>
  );
}
