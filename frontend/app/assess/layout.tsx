import type { Metadata } from "next";

/**
 * Metadata for /assess.
 *
 * Lives in a layout because the page itself is a client component, and
 * `export const metadata` is server-only. A layout wrapping a single page is
 * the standard way round that in the App Router — it costs one file and avoids
 * splitting the page into a server shell just to carry a title.
 */
export const metadata: Metadata = {
  title: "Assess a model",
  description:
    "Describe a proposed model and get a pre-registration risk assessment " +
    "against the RBI's 2026 draft Model Risk Management guidance. Every " +
    "finding cites the principle it came from. Upload a dataset for " +
    "overfitting, imbalance, proxy-attribute and drift diagnostics.",
  openGraph: {
    title: "Assess a model · AI Model Governance Registry",
    description:
      "A pre-registration risk assessment against published RBI principles — " +
      "a rules engine, not a black-box failure score.",
  },
};

// Wrapped in a fragment rather than returning `children` bare. Both are
// legal, but a layout returning a raw ReactNode instead of a JSX element has
// been a source of client-manifest errors in the App Router, and the fragment
// costs nothing.
export default function AssessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
