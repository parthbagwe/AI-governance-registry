"use client";

import { useMemo } from "react";

/**
 * Bull against bear.
 *
 * The two animals are distinguished almost entirely by their back line, which
 * is the thing to get right and the thing most attempts miss:
 *
 *   A bull's mass sits at the shoulder, its head drops *below* the shoulder
 *   line to bring the horns forward, and its back slopes down toward the rump.
 *   A bear's hump also sits forward, but its head carries low on a long snout,
 *   its rump is lower still, and its legs are short and plantigrade.
 *
 * Get those two profiles right and the silhouettes read instantly even at
 * small sizes. Add detail beyond that and they start landing in the uncanny
 * middle — clearly attempting realism, clearly not achieving it.
 *
 * The outcome is random per mount. That isn't decoration: a governance tool
 * whose loading screen always showed the market going up would be quietly
 * lying about the thing it exists to watch.
 */

const BULL = "#34d399";
const BEAR = "#f87171";

/** Bull, drawn facing right in a 200×132 local space. */
function Bull({ colour, dim }: { colour: string; dim: boolean }) {
  const fill = dim ? "rgba(52, 211, 153, 0.30)" : colour;
  return (
    <g fill={fill} stroke={fill}>
      {/* Rear legs — planted, driving forward */}
      <path
        d="M40 84 L54 84 L57 124 Q57 128 51 128 L45 128 Q40 128 40 124 Z"
        strokeWidth="0"
      />
      <path
        d="M58 88 L70 88 L72 124 Q72 128 67 128 L62 128 Q58 128 58 124 Z"
        strokeWidth="0"
      />

      {/* Body. The back rises from the rump to a heavy shoulder, then drops
          away to the neck — the profile that makes it a bull. */}
      <path
        d="M26 66
           Q30 40 62 34
           Q92 29 116 40
           L140 54
           L134 76
           L112 86
           Q76 98 44 90
           Q24 84 26 66 Z"
        strokeWidth="0"
      />

      {/* Front legs, braced under the shoulder */}
      <path
        d="M112 84 L126 84 L129 124 Q129 128 124 128 L118 128 Q113 128 113 124 Z"
        strokeWidth="0"
      />
      <path
        d="M128 80 L140 80 L144 122 Q144 126 139 126 L134 126 Q129 126 129 122 Z"
        strokeWidth="0"
      />

      {/* Head, carried low so the horns lead */}
      <path
        d="M130 48
           Q160 50 175 70
           Q184 83 175 92
           Q158 99 143 88
           Q132 74 130 56 Z"
        strokeWidth="0"
      />
      {/* Muzzle */}
      <path d="M168 84 Q184 84 186 91 Q186 97 175 97 Q167 95 166 90 Z" strokeWidth="0" />

      {/* Horns, sweeping up and forward */}
      <path
        d="M152 44 Q170 28 190 34"
        fill="none"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <path
        d="M140 48 Q152 34 170 40"
        fill="none"
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* Ear */}
      <path d="M136 56 Q124 50 120 58 Q124 66 136 64 Z" strokeWidth="0" />

      {/* Tail with tuft */}
      <path
        d="M27 60 Q13 50 14 33"
        fill="none"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <circle cx="14" cy="28" r="5" strokeWidth="0" />
    </g>
  );
}

/** Bear, drawn facing right in a 200×132 local space; mirrored by the caller. */
function Bear({ colour, dim }: { colour: string; dim: boolean }) {
  const fill = dim ? "rgba(248, 113, 113, 0.30)" : colour;
  return (
    <g fill={fill} stroke={fill}>
      {/* Rear legs — short, flat-footed */}
      <path
        d="M40 88 L56 88 L58 118 Q62 118 64 124 Q64 128 56 128 L44 128 Q40 128 40 122 Z"
        strokeWidth="0"
      />

      {/* Body. Shoulder hump forward, rump noticeably lower — the reverse of
          the bull's line, and the fastest way to tell them apart. */}
      <path
        d="M28 74
           Q30 52 58 44
           Q92 33 122 44
           Q142 52 146 68
           L142 84
           Q100 98 62 96
           Q30 92 28 74 Z"
        strokeWidth="0"
      />

      {/* Front legs */}
      <path
        d="M104 86 L120 86 L122 118 Q126 118 128 124 Q128 128 120 128 L108 128 Q104 128 104 122 Z"
        strokeWidth="0"
      />

      {/* Head, low and heavy */}
      <path
        d="M134 56
           Q160 54 172 70
           Q180 82 171 91
           Q154 98 141 86
           Q133 72 134 62 Z"
        strokeWidth="0"
      />
      {/* Long snout — the single most bear-identifying feature at this scale */}
      <path
        d="M166 74 Q190 74 192 83 Q192 92 176 92 Q166 90 164 83 Z"
        strokeWidth="0"
      />
      <circle cx="188" cy="82" r="3" fill="rgba(0,0,0,0.35)" strokeWidth="0" />

      {/* Round ear, set high and back */}
      <circle cx="137" cy="49" r="9" strokeWidth="0" />

      {/* Stub tail */}
      <circle cx="30" cy="70" r="6" strokeWidth="0" />
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
      <svg viewBox="0 0 620 220" className="w-full" aria-hidden="true">
        {/* Ground, drawn outward from the middle */}
        <line
          x1="50"
          x2="570"
          y1="176"
          y2="176"
          stroke="rgba(148,163,184,0.16)"
          strokeWidth="1.2"
          style={{
            strokeDasharray: 520,
            animation: "draw 760ms cubic-bezier(0.16,1,0.3,1) both",
            ["--dash" as string]: "520",
          }}
        />

        {/* Contact shadows. Cheap, and they stop both animals looking like
            stickers floating above the line. */}
        <ellipse
          cx="180"
          cy="178"
          rx="86"
          ry="7"
          fill="rgba(0,0,0,0.35)"
          style={{ animation: "fade 620ms ease-out both", animationDelay: "120ms" }}
        />
        <ellipse
          cx="440"
          cy="178"
          rx="86"
          ry="7"
          fill="rgba(0,0,0,0.35)"
          style={{ animation: "fade 620ms ease-out both", animationDelay: "120ms" }}
        />

        {/* Bull, entering from the left */}
        <g
          style={{
            animation: `charge-in-left 640ms cubic-bezier(0.34, 1.28, 0.64, 1) both${
              bullWins
                ? ", surge-right 950ms cubic-bezier(0.5,0,0.2,1) 820ms both"
                : ", recoil-left 950ms cubic-bezier(0.5,0,0.2,1) 820ms both"
            }`,
          }}
        >
          <g transform="translate(84, 46)">
            <Bull colour={BULL} dim={!bullWins} />
          </g>
        </g>

        {/* Bear, entering from the right, mirrored to face inward */}
        <g
          style={{
            animation: `charge-in-right 640ms cubic-bezier(0.34, 1.28, 0.64, 1) both${
              !bullWins
                ? ", surge-left 950ms cubic-bezier(0.5,0,0.2,1) 820ms both"
                : ", recoil-right 950ms cubic-bezier(0.5,0,0.2,1) 820ms both"
            }`,
          }}
        >
          <g transform="translate(536, 46) scale(-1, 1)">
            <Bear colour={BEAR} dim={bullWins} />
          </g>
        </g>

        {/* Impact where they meet */}
        <g
          style={{
            animation: "clash-flash 560ms ease-out both",
            animationDelay: "640ms",
            transformOrigin: "310px 120px",
          }}
        >
          {[15, 70, 125, 180, 235, 290, 345].map((angle) => {
            const rad = (angle * Math.PI) / 180;
            const inner = 12;
            const outer = 34;
            return (
              <line
                key={angle}
                x1={310 + Math.cos(rad) * inner}
                y1={120 + Math.sin(rad) * inner}
                x2={310 + Math.cos(rad) * outer}
                y2={120 + Math.sin(rad) * outer}
                stroke={winner}
                strokeWidth="3"
                strokeLinecap="round"
                opacity="0.8"
              />
            );
          })}
        </g>

        {/* Dust kicked up along the ground at the point of contact */}
        <g
          style={{
            animation: "clash-flash 780ms ease-out both",
            animationDelay: "700ms",
            transformOrigin: "310px 176px",
          }}
        >
          {[-52, -30, -14, 14, 30, 52].map((dx, i) => (
            <circle
              key={dx}
              cx={310 + dx}
              cy={172 - (i % 3) * 5}
              r={3.5 - (i % 3) * 0.6}
              fill="rgba(148,163,184,0.5)"
            />
          ))}
        </g>

        {/* The verdict, as a trend arrow on the right */}
        <g
          style={{
            animation: "fade 560ms ease-out both",
            animationDelay: "1250ms",
          }}
        >
          <line
            x1="580"
            x2="580"
            y1={bullWins ? "128" : "78"}
            y2={bullWins ? "78" : "128"}
            stroke={winner}
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            d={bullWins ? "M568 92 l12 -14 l12 14" : "M568 114 l12 14 l12 -14"}
            fill="none"
            stroke={winner}
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      </svg>
    </div>
  );
}
