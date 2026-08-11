import { ImageResponse } from "next/og";

/**
 * The link preview card.
 *
 * Generated rather than a checked-in PNG, so it can't drift out of sync with
 * the site the way an exported image inevitably does. It's also the single
 * highest-leverage thing on that pre-launch checklist for this project
 * specifically: this link gets pasted into applications, LinkedIn posts and
 * messages, and a blank grey preview makes a serious piece of work look like
 * an abandoned repo.
 *
 * next/og renders with Satori, which supports a deliberate subset of CSS —
 * flexbox only, no grid, no external stylesheets, every element needs an
 * explicit display. Anything fancier fails at build rather than degrading, so
 * this is kept to blocks and flex.
 */

export const runtime = "nodejs";
export const alt =
  "AI Model Governance Registry — risk-tiered approval, drift monitoring, and an audit trail for banking AI";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// A fixed candlestick series. Hardcoded rather than random: a share image gets
// cached by every platform that fetches it, so regenerating a different chart
// each build would produce inconsistent previews for the same link.
const CANDLES: { h: number; y: number; up: boolean }[] = [
  { h: 42, y: 150, up: true },
  { h: 28, y: 168, up: false },
  { h: 56, y: 132, up: true },
  { h: 34, y: 120, up: true },
  { h: 24, y: 138, up: false },
  { h: 62, y: 96, up: true },
  { h: 30, y: 84, up: true },
  { h: 46, y: 100, up: false },
  { h: 38, y: 70, up: true },
  { h: 70, y: 40, up: true },
  { h: 26, y: 34, up: false },
  { h: 50, y: 14, up: true },
];

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background:
            "linear-gradient(135deg, #080b14 0%, #0d1220 55%, #121829 100%)",
          padding: "64px 72px",
          fontFamily: "sans-serif",
        }}
      >
        {/* Masthead */}
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {/* The mark, rebuilt from divs. Satori can't rasterise an emoji
              without a font that carries it, and an emoji standing in for a
              logo is one of the more obvious signs nobody drew anything. */}
          <div
            style={{
              display: "flex",
              width: 46,
              height: 46,
              borderRadius: 12,
              background: "rgba(56,189,248,0.14)",
              border: "1px solid rgba(56,189,248,0.3)",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 3,
                alignItems: "flex-start",
              }}
            >
              <div style={{ display: "flex", width: 11, height: 4, borderRadius: 1.5, background: "rgba(56,189,248,0.55)" }} />
              <div style={{ display: "flex", width: 17, height: 4, borderRadius: 1.5, background: "rgba(56,189,248,0.8)" }} />
              <div style={{ display: "flex", width: 22, height: 4, borderRadius: 1.5, background: "#38bdf8" }} />
            </div>
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 21,
              color: "#94a3b8",
              letterSpacing: 1,
            }}
          >
            MODEL RISK MANAGEMENT
          </div>
        </div>

        {/* Headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div
            style={{
              display: "flex",
              fontSize: 66,
              fontWeight: 700,
              color: "#ffffff",
              lineHeight: 1.08,
              letterSpacing: -1.8,
              maxWidth: 900,
            }}
          >
            Every model the bank runs, and whether it earned the right to run.
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 25,
              color: "#94a3b8",
              maxWidth: 820,
              lineHeight: 1.4,
            }}
          >
            Risk-tiered approval gates, an emergency kill switch, live drift
            monitoring on real market data, and an audit trail nothing can
            rewrite.
          </div>
          {/* Note: no em dashes anywhere in this file's copy. They're a
              legitimate mark, but at the density they tend to appear in
              generated text they read as a signature. */}
        </div>

        {/* Footer: chips on the left, a chart on the right */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", gap: 12 }}>
            {["FastAPI", "Next.js", "XGBoost", "Evidently AI"].map((tag) => (
              <div
                key={tag}
                style={{
                  display: "flex",
                  padding: "9px 18px",
                  borderRadius: 999,
                  border: "1px solid rgba(148,163,184,0.22)",
                  color: "#cbd5e1",
                  fontSize: 20,
                }}
              >
                {tag}
              </div>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: 9,
              height: 210,
            }}
          >
            {CANDLES.map((c, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  width: 15,
                  height: c.h,
                  marginBottom: c.y,
                  borderRadius: 3,
                  background: c.up ? "#34d399" : "#f87171",
                }}
              />
            ))}
          </div>
        </div>
      </div>
    ),
    size
  );
}
