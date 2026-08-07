"use client";

import { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { API_BASE } from "@/lib/api";

/**
 * Full-screen preloader, shown once per session.
 *
 * The important decision here is that the progress is *real*. Most preloaders
 * are a timed animation with a number attached — theatre that makes a fast
 * site slower and lies on a slow one. This one pings the API's /health
 * endpoint and completes when the backend actually answers.
 *
 * That matters specifically for this project: the deployed API sits on a free
 * tier that sleeps after fifteen minutes idle, so a cold start genuinely takes
 * 30-60 seconds. A fake 1.5s bar would finish, hand over to an empty page, and
 * leave the user staring at nothing. Instead the counter eases toward 90 and
 * waits, and after six seconds it explains itself rather than just spinning.
 *
 * Shown once per session, not once per navigation — a preloader you sit
 * through every time you click "back" is a tax, not a flourish.
 */

const SESSION_KEY = "governance-registry-preloaded";
const SLOW_HINT_MS = 6000;
const GIVE_UP_MS = 30000;

function healthUrl(): string {
  // API_BASE ends in /api/v1; /health lives at the service root.
  return `${API_BASE.replace(/\/api\/v\d+\/?$/, "")}/health`;
}

export function Preloader() {
  const [active, setActive] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const [slow, setSlow] = useState(false);
  const settled = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (sessionStorage.getItem(SESSION_KEY)) return;

    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reduced) {
      sessionStorage.setItem(SESSION_KEY, "1");
      return;
    }

    setActive(true);
    document.body.style.overflow = "hidden";

    const started = performance.now();

    // Eases toward 90 and stops there. The last 10% belongs to the backend
    // actually answering — a bar that reaches 100 before the data arrives is
    // the thing that makes preloaders feel dishonest.
    let frame = 0;
    const tick = (now: number) => {
      if (!settled.current) {
        const t = Math.min((now - started) / 2200, 1);
        setProgress(90 * (1 - Math.pow(1 - t, 3)));
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);

    const slowTimer = window.setTimeout(() => setSlow(true), SLOW_HINT_MS);

    const finish = () => {
      if (settled.current) return;
      settled.current = true;
      cancelAnimationFrame(frame);
      window.clearTimeout(slowTimer);
      setProgress(100);
      sessionStorage.setItem(SESSION_KEY, "1");

      // Brief hold at 100 so the number is legible, then the curtain lifts.
      window.setTimeout(() => setLeaving(true), 260);
      window.setTimeout(() => {
        setActive(false);
        document.body.style.overflow = "";
      }, 1160);
    };

    // Never hold the page hostage. If the API is unreachable the app itself
    // renders a proper connection error — far more useful than a loader
    // spinning forever with no explanation.
    const giveUp = window.setTimeout(finish, GIVE_UP_MS);

    fetch(healthUrl(), { cache: "no-store" })
      .then(finish)
      .catch(finish)
      .finally(() => window.clearTimeout(giveUp));

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(slowTimer);
      window.clearTimeout(giveUp);
      document.body.style.overflow = "";
    };
  }, []);

  if (!active) return null;

  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col justify-between bg-ink-950 px-6 py-10 transition-transform duration-[900ms] sm:px-12 ${
        leaving ? "-translate-y-full" : "translate-y-0"
      }`}
      style={{ transitionTimingFunction: "cubic-bezier(0.76, 0, 0.24, 1)" }}
      aria-hidden="true"
    >
      <div className="fade-in flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-sky-500/15 ring-1 ring-inset ring-sky-400/25">
          <ShieldCheck className="h-5 w-5 text-sky-300" />
        </span>
        <span className="text-sm font-medium text-slate-300">
          AI Model Governance Registry
        </span>
      </div>

      <div className="flex flex-col items-start gap-6">
        <p
          className="fade-in max-w-lg text-[clamp(1.4rem,3.6vw,2.2rem)] font-semibold leading-[1.15] tracking-[-0.02em] text-white"
          style={{ animationDelay: "0.2s" }}
        >
          Reading the register
        </p>

        <div className="w-full">
          <div className="h-px w-full overflow-hidden bg-white/10">
            <div
              className="h-full bg-sky-400 transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="mt-4 flex items-baseline justify-between gap-4">
            <p
              className={`text-xs transition-opacity duration-500 ${
                slow ? "text-amber-300/80 opacity-100" : "opacity-0"
              }`}
            >
              Waking the server — free hosting sleeps when idle. This can take
              up to a minute.
            </p>
            <span className="font-mono text-4xl font-semibold tabular-nums leading-none tracking-[-0.03em] text-white">
              {Math.round(progress)}
              <span className="text-slate-600">%</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
