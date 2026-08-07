"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Scroll-triggered reveal.
 *
 * IntersectionObserver rather than a scroll listener: the browser does the
 * work off the main thread, so a long audit trail doesn't cost frames while
 * scrolling. Each element unobserves itself once shown — content that
 * re-animates every time it passes the viewport is irritating on the second
 * pass and infuriating on the tenth.
 */
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // If the browser can't observe, show it. Never hide content behind a
    // capability check.
    if (typeof IntersectionObserver === "undefined") {
      setShown(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.unobserve(entry.target);
        }
      },
      // Fires slightly before the element reaches the viewport edge, so it's
      // already settled by the time it's properly in view.
      { rootMargin: "0px 0px -60px 0px", threshold: 0.05 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal ${shown ? "is-visible" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/**
 * Counts a number up on first paint.
 *
 * Uses requestAnimationFrame against wall-clock time rather than a fixed step
 * count, so it takes the same duration on a 60Hz and a 144Hz display. The
 * easing is the same curve as the CSS reveals, so the two read as one system.
 *
 * Deliberately capped: over ~2 seconds this stops feeling like polish and
 * starts feeling like the page is slow.
 */
export function CountUp({
  value,
  duration = 900,
  decimals = 0,
  className = "",
}: {
  value: number;
  duration?: number;
  decimals?: number;
  className?: string;
}) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reduced || value === 0) {
      setDisplay(value);
      return;
    }

    let frame = 0;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      // Same shape as --ease-out-soft: fast start, long settle.
      const eased = 1 - Math.pow(1 - t, 4);
      setDisplay(value * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return (
    <span className={className}>
      {decimals > 0 ? display.toFixed(decimals) : Math.round(display)}
    </span>
  );
}
