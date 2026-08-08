"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { resetScroll } from "@/components/SmoothScroll";
import { CandlestickAnimation } from "@/components/CandlestickAnimation";

/**
 * Page transition: a market chart draws itself while the next page loads.
 *
 * The visual isn't arbitrary. This system monitors FX markets, so the loading
 * state shows the thing it actually watches — a price series forming. A
 * spinner would say nothing about what's happening; a chart drawing itself
 * says "market data is being read", which happens to be true.
 *
 * Structure: a full-bleed panel rises from the bottom, the chart builds inside
 * it, then the panel keeps rising and exits through the top. It never
 * retracts. A cover that reverses out the way it came reads as undo; one that
 * travels through reads as a transition.
 *
 * It also solves a real problem. The App Router swaps routes instantly, but
 * the page underneath then fires several requests before it can render. With
 * nothing over that gap you get a click, a pause, and a jump — which reads as
 * the site hanging even when nothing is wrong.
 */

const COVER_MS = 420;
const HOLD_MS = 1100; // long enough for the chart to finish drawing
const REVEAL_MS = 520;
const TOTAL = COVER_MS + HOLD_MS + REVEAL_MS;

export function RouteTransition() {
  const pathname = usePathname();
  const previous = useRef<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "covering" | "revealing">("idle");
  // Forces a fresh chart on every transition — a fixed series would start to
  // look like a static image by the third navigation.
  const [seed, setSeed] = useState(0);

  useEffect(() => {
    // Skip the first render; the preloader owns that moment and stacking two
    // entrance animations reads as a stutter.
    if (previous.current === null) {
      previous.current = pathname;
      return;
    }
    if (previous.current === pathname) return;
    previous.current = pathname;

    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reduced) {
      resetScroll();
      return;
    }

    setSeed(Math.floor(Math.random() * 1_000_000));
    setPhase("covering");

    const toReveal = window.setTimeout(() => {
      // Scroll resets while fully covered, so the jump is never visible.
      resetScroll();
      setPhase("revealing");
    }, COVER_MS + HOLD_MS);

    const toIdle = window.setTimeout(() => setPhase("idle"), TOTAL);

    return () => {
      window.clearTimeout(toReveal);
      window.clearTimeout(toIdle);
    };
  }, [pathname]);

  if (phase === "idle") return null;

  const covering = phase === "covering";

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[90] overflow-hidden"
      aria-hidden="true"
    >
      <div
        className="absolute inset-0 flex flex-col items-center justify-center bg-ink-950 px-6"
        style={{
          animationName: covering ? "panel-rise-in" : "panel-rise-out",
          animationDuration: `${covering ? COVER_MS : REVEAL_MS}ms`,
          animationTimingFunction: "cubic-bezier(0.76, 0, 0.24, 1)",
          animationFillMode: "both",
          willChange: "transform",
        }}
      >
        <div className="w-full max-w-3xl">
          {covering && (
            <CandlestickAnimation
              seed={seed}
              className="opacity-90"
              candleMs={250}
              staggerMs={32}
            />
          )}
        </div>

        <p
          className="fade-in mt-6 font-mono text-[11px] uppercase tracking-[0.22em] text-slate-600"
          style={{ animationDelay: "160ms" }}
        >
          Reading the register
        </p>
      </div>
    </div>
  );
}
