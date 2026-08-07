"use client";

import { useEffect } from "react";
import Lenis from "lenis";

/**
 * Inertial scrolling.
 *
 * This is the single change that separates a site that feels *designed* from
 * one that feels assembled — and it's also the easiest thing to overdo. Studio
 * sites often run a duration near 2s, which looks extraordinary in a showreel
 * and is maddening when you're trying to find a row in a table. 1.05s with a
 * steep exponential is the compromise: the page carries momentum and settles
 * softly, but a flick still lands roughly where you meant it to.
 *
 * Turned off entirely for anyone who has asked their OS to reduce motion.
 * Hijacking scroll is the most invasive thing on this page, and for someone
 * with a vestibular disorder it's the difference between usable and not.
 */
export function SmoothScroll() {
  useEffect(() => {
    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reduced) return;

    // Touch devices already have excellent native inertia; overriding it makes
    // a phone feel broken. Left alone deliberately.
    const lenis = new Lenis({
      duration: 1.05,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      syncTouch: false,
    });

    let frame = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      frame = requestAnimationFrame(raf);
    };
    frame = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(frame);
      lenis.destroy();
    };
  }, []);

  return null;
}
