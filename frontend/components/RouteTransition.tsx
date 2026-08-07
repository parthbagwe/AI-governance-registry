"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { resetScroll } from "@/components/SmoothScroll";

/**
 * Covers the gap between clicking a link and the new page having data.
 *
 * The App Router swaps the route instantly, but the page underneath then fires
 * several requests before it has anything to show. Without something covering
 * that window you get a click, a pause, and then a jump — which reads as the
 * site hanging even when nothing is wrong.
 *
 * Two panels sweep across from opposite edges and retract. The retraction is
 * the slower half deliberately: a curtain that snaps open feels like a glitch,
 * one that draws back feels like a transition.
 *
 * It also resets scroll. Lenis owns the scroll position, so without an
 * explicit reset you arrive at a new page already scrolled to wherever you
 * were on the last one.
 */

const COVER_MS = 380;
const HOLD_MS = 140;
const REVEAL_MS = 620;

export function RouteTransition() {
  const pathname = usePathname();
  const previous = useRef<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "covering" | "revealing">("idle");

  useEffect(() => {
    // Skip the very first render — the preloader already owns that moment, and
    // stacking two entrance animations looks like a stutter.
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

    setPhase("covering");
    const timers: number[] = [];

    timers.push(
      window.setTimeout(() => {
        // Scroll is reset at full cover, so the jump is never visible.
        resetScroll();
        setPhase("revealing");
      }, COVER_MS + HOLD_MS)
    );

    timers.push(
      window.setTimeout(() => setPhase("idle"), COVER_MS + HOLD_MS + REVEAL_MS)
    );

    return () => timers.forEach(window.clearTimeout);
  }, [pathname]);

  if (phase === "idle") return null;

  const covered = phase === "covering";

  return (
    <div className="pointer-events-none fixed inset-0 z-[90]" aria-hidden="true">
      {/* Top panel sweeps down, bottom panel sweeps up — they meet in the
          middle, which hides the seam better than a single full-height wipe. */}
      <div
        className="absolute inset-x-0 top-0 h-1/2 bg-ink-950"
        style={{
          transform: covered ? "translateY(0)" : "translateY(-101%)",
          transition: `transform ${covered ? COVER_MS : REVEAL_MS}ms cubic-bezier(0.76, 0, 0.24, 1)`,
        }}
      />
      <div
        className="absolute inset-x-0 bottom-0 h-1/2 bg-ink-950"
        style={{
          transform: covered ? "translateY(0)" : "translateY(101%)",
          transition: `transform ${covered ? COVER_MS : REVEAL_MS}ms cubic-bezier(0.76, 0, 0.24, 1)`,
          // A beat behind the top panel, so the two edges don't move as one
          // slab. Small asymmetries are most of what makes motion feel crafted.
          transitionDelay: covered ? "40ms" : "0ms",
        }}
      />

      {/* A hairline that races across the seam while the panels are closed. */}
      <div className="absolute inset-x-0 top-1/2 flex -translate-y-1/2 justify-center overflow-hidden">
        <div
          className="h-px bg-sky-400/70"
          style={{
            width: covered ? "min(340px, 60vw)" : "0px",
            transition: `width ${covered ? COVER_MS + HOLD_MS : 180}ms cubic-bezier(0.16, 1, 0.3, 1)`,
          }}
        />
      </div>
    </div>
  );
}
