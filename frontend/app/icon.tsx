import { ImageResponse } from "next/og";

/**
 * Favicon, generated from the same mark as the header.
 *
 * A missing favicon leaves the browser's default page glyph in the tab, which
 * is one of the more reliable signals that nobody finished the job. Generating
 * it rather than checking in a .ico means it can't fall out of sync with the
 * logo, and there's no binary asset in the repo to maintain.
 *
 * Drawn slightly heavier than the header version: at 32px the thin gate rule
 * disappears entirely, so the proportions have to be adjusted rather than
 * simply scaled.
 */

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0d1220",
          borderRadius: 7,
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
          <div
            style={{
              display: "flex",
              width: 9,
              height: 4,
              borderRadius: 1.5,
              background: "rgba(56,189,248,0.55)",
            }}
          />
          <div
            style={{
              display: "flex",
              width: 13,
              height: 4,
              borderRadius: 1.5,
              background: "rgba(56,189,248,0.8)",
            }}
          />
          <div
            style={{
              display: "flex",
              width: 17,
              height: 4,
              borderRadius: 1.5,
              background: "#38bdf8",
            }}
          />
        </div>
      </div>
    ),
    size
  );
}
