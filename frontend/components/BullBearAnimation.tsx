"use client";

import { useMemo } from "react";

/**
 * Bull against bear.
 *
 * Built from a handful of rounded primitives rather than one traced outline.
 * A detailed silhouette drawn by hand tends to land in the uncanny middle —
 * detailed enough that you read it as an attempt at realism, not good enough
 * to succeed at it. Chunky geometry reads as a deliberate flat-graphic style
 * instead, which is both more honest and easier to keep on-brand.
 *
 * The outcome is random per mount: sometimes the bull pushes through,
 * sometimes the bear does. That's not decoration — a governance tool whose
 * loading screen always showed the market going up would be quietly telling
 * a lie about what it exists to watch.
 */

const BULL = "#34d399";
const BEAR = "#f87171";

function Bull({ colour }: { colour: string }) {
  return (
    <g fill={colour}>
      {/* Rear leg and haunch */}
      <rect x="30" y="86" width="13" height="42" rx="5" />
      <rect x="47" y="90" width="12" height="38" rx="5" />
      {/* Body — the raised shoulder is what makes it read as a bull rather
          than a generic quadruped */}
      <path d="M24 84 Q28 46 62 42 Q96 38 118 54 Q132 64 138 76 L138 92 Q100 100 62 98 Q34 96 24 84 Z" />
      {/* Front legs, braced forward in a charge */}
      <rect x="104" y="88" width="13" height="40" rx="5" transform="rotate(9 110 108)" />
      <rect x="120" y="86" width="12" height="42" rx="5" transform="rotate(15 126 107)" />
      {/* Lowered head */}
      <path d="M132 60 Q156 58 168 74 Q176 85 172 96 Q160 104 146 96 Q134 86 132 72 Z" />
      {/* Horns, sweeping forward */}
      <path
        d="M150 58 Q166 44 184 48"
        stroke={colour}
        strokeWidth="7"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M144 62 Q156 50 172 56"
        stroke={colour}
        strokeWidth="6"
        strokeLinecap="round"
        fill="none"
      />
      {/* Tail */}
      <path
        d="M25 76 Q10 68 8 52"
        stroke={colour}
        strokeWidth="5"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="8" cy="48" r="4" />
    </g>
  );
}

function Bear({ colour }: { colour: string }) {
  return (
    <g fill={colour}>
      {/* Rear legs */}
      <rect x="146" y="90" width="14" height="38" rx="6" />
      <rect x="128" y="92" width="13" height="36" rx="6" />
      {/* Body — the shoulder hump sits forward on a bear, opposite to the
          bull's raised rear */}
      <path d="M42 84 Q40 56 66 48 Q96 38 128 44 Q158 50 166 74 L166 94 Q120 102 78 100 Q50 98 42 84 Z" />
      {/* Front legs */}
      <rect x="58" y="88" width="14" height="40" rx="6" transform="rotate(-8 65 108)" />
      <rect x="76" y="90" width="13" height="38" rx="6" transform="rotate(-4 82 109)" />
      {/* Head, low and forward */}
      <path d="M56 62 Q34 60 24 76 Q18 88 26 96 Q40 104 54 94 Q62 84 60 70 Z" />
      {/* Snout */}
      <path d="M28 82 Q14 82 12 90 Q12 97 22 97 Q30 96 32 90 Z" />
      <circle cx="14" cy="88" r="3" opacity="0.55" />
      {/* Ear */}
      <circle cx="56" cy="58" r="8" />
    </g>
  );
}

export function BullBearAnimation({
  seed,
  className = "",
}: {
  seed?: number;
  className?: string;
}) {
  const bullWins = useMemo(() => {
    const s = seed ?? Math.floor(Math.random() * 1_000_000);
    return s % 2 === 0;
  }, [seed]);

  const winner = bullWins ? BULL : BEAR;

  return (
    <div className={`w-full ${className}`}>
      <svg viewBox="0 0 560 190" className="w-full" aria-hidden="true">
        {/* Ground line, drawing outward from the centre */}
        <line
          x1="40"
          x2="520"
          y1="150"
          y2="150"
          stroke="rgba(148,163,184,0.14)"
          strokeWidth="1"
          style={{
            strokeDasharray: 480,
            animation: "draw 700ms cubic-bezier(0.16,1,0.3,1) both",
            ["--dash" as string]: "480",
          }}
        />

        {/* Bull, entering from the left */}
        <g
          style={{
            animation: `charge-in-left 620ms cubic-bezier(0.34, 1.3, 0.64, 1) both${
              bullWins ? ", surge-right 900ms cubic-bezier(0.5,0,0.2,1) 780ms both" : ""
            }`,
          }}
        >
          <g transform="translate(60, 16)">
            <Bull colour={bullWins ? BULL : "rgba(52, 211, 153, 0.42)"} />
          </g>
        </g>

        {/* Bear, entering from the right and mirrored to face inward */}
        <g
          style={{
            animation: `charge-in-right 620ms cubic-bezier(0.34, 1.3, 0.64, 1) both${
              !bullWins ? ", surge-left 900ms cubic-bezier(0.5,0,0.2,1) 780ms both" : ""
            }`,
          }}
        >
          <g transform="translate(500, 16) scale(-1, 1)">
            <Bear colour={!bullWins ? BEAR : "rgba(248, 113, 113, 0.42)"} />
          </g>
        </g>

        {/* Impact mark where they meet */}
        <g
          style={{
            animation: "clash-flash 520ms ease-out both",
            animationDelay: "600ms",
            transformOrigin: "280px 96px",
          }}
        >
          {[0, 60, 120, 180, 240, 300].map((angle) => (
            <line
              key={angle}
              x1="280"
              y1="96"
              x2={280 + Math.cos((angle * Math.PI) / 180) * 30}
              y2={96 + Math.sin((angle * Math.PI) / 180) * 30}
              stroke={winner}
              strokeWidth="2.5"
              strokeLinecap="round"
              opacity="0.7"
            />
          ))}
        </g>

        {/* The verdict, as a trend arrow */}
        <g
          style={{
            animation: "fade 500ms ease-out both",
            animationDelay: "1150ms",
          }}
        >
          <path
            d={
              bullWins
                ? "M300 46 L340 46 L340 86"
                : "M300 46 L340 46 L340 86"
            }
            fill="none"
            stroke={winner}
            strokeWidth="0"
          />
          <path
            d={bullWins ? "M356 62 l14 -14 l14 14" : "M356 48 l14 14 l14 -14"}
            fill="none"
            stroke={winner}
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            transform="translate(120, 0)"
          />
          <line
            x1="490"
            x2="490"
            y1={bullWins ? "78" : "48"}
            y2={bullWins ? "48" : "78"}
            stroke={winner}
            strokeWidth="3.5"
            strokeLinecap="round"
          />
        </g>
      </svg>
    </div>
  );
}
