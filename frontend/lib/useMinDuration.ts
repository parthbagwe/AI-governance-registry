"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Holds a loading state open for a minimum duration.
 *
 * A skeleton that appears and vanishes in 120ms is worse than no skeleton:
 * the eye registers a flash and reads it as a rendering fault rather than as
 * loading. Below roughly 400ms, an interface feels *more* responsive if it
 * shows a settled loading state than if it flickers through one.
 *
 * This only ever adds time when the data arrives quickly. When a request is
 * genuinely slow the floor has already elapsed and costs nothing.
 */
export function useMinDuration(active: boolean, minMs = 500): boolean {
  const [held, setHeld] = useState(active);
  const startedAt = useRef<number | null>(active ? Date.now() : null);

  useEffect(() => {
    if (active) {
      startedAt.current = Date.now();
      setHeld(true);
      return;
    }

    const elapsed = Date.now() - (startedAt.current ?? Date.now());
    const remaining = minMs - elapsed;

    if (remaining <= 0) {
      setHeld(false);
      return;
    }

    const timer = window.setTimeout(() => setHeld(false), remaining);
    return () => window.clearTimeout(timer);
  }, [active, minMs]);

  return held;
}
