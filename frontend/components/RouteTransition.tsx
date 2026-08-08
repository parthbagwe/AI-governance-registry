"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { resetScroll } from "@/components/SmoothScroll";
import { LoadingVisual } from "@/components/LoadingVisual";

/**
 * Page transition: a market visual plays while the next page loads.
 *
 * The visual isn't arbitrary. This system monitors markets, so the loading
 * state shows the thing it actually watches — a price series forming, a tape
 * running, or bull against bear. A spinner would say nothing about what's
 * happening; these say "market data is being read", which happens to be true.
 *
 * One of three is chosen at random each time. A loading screen gets seen
 * dozens of times in a session, and a fixed animation stops registering after
 * the third viewing — at which point it's just a delay with decoration on it.
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
        {/* Only rendered while covering — mounting it during the reveal would
            restart every animation just as the panel is leaving, which shows
            up as a flicker on the way out. */}
        <div className="w-full max-w-3xl">
          {covering && <LoadingVisual seed={seed} />}
        </div>
      </div>
    </div>
  );
}
