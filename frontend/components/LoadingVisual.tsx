"use client";

import { useMemo } from "react";

import { BullBearAnimation } from "@/components/BullBearAnimation";
import { CandlestickAnimation } from "@/components/CandlestickAnimation";
import { TickerAnimation } from "@/components/TickerAnimation";

/**
 * Picks one of three market visuals at random.
 *
 * Three rather than one because a loading screen is seen dozens of times in a
 * session and a fixed animation stops being noticed after the third viewing —
 * at which point it's just a delay. Variety keeps the wait from feeling like
 * the same wait.
 *
 * Each carries its own caption, because the visual and the label have to agree.
 * A candlestick chart under "market makes its case" would be nonsense; the
 * words are part of the picture.
 */

export type VisualVariant = "candles" | "bullbear" | "ticker";

const VARIANTS: VisualVariant[] = ["candles", "bullbear", "ticker"];

const CAPTIONS: Record<VisualVariant, string> = {
  candles: "Reading the register",
  bullbear: "Weighing both sides",
  ticker: "Watching the tape",
};

export function pickVariant(seed?: number): VisualVariant {
  const s = seed ?? Math.floor(Math.random() * 1_000_000);
  return VARIANTS[s % VARIANTS.length];
}

export function LoadingVisual({
  seed,
  variant,
  showCaption = true,
}: {
  seed?: number;
  variant?: VisualVariant;
  showCaption?: boolean;
}) {
  const chosen = useMemo(
    () => variant ?? pickVariant(seed),
    [variant, seed]
  );

  return (
    <div className="flex w-full flex-col items-center">
      <div className="w-full">
        {chosen === "candles" && (
          <CandlestickAnimation seed={seed} className="opacity-90" candleMs={250} staggerMs={32} />
        )}
        {chosen === "bullbear" && (
          <BullBearAnimation seed={seed} className="opacity-95" />
        )}
        {chosen === "ticker" && <TickerAnimation seed={seed} />}
      </div>

      {showCaption && (
        <p
          className="fade-in mt-6 font-mono text-[11px] uppercase tracking-[0.22em] text-slate-600"
          style={{ animationDelay: "220ms" }}
        >
          {CAPTIONS[chosen]}
        </p>
      )}
    </div>
  );
}
