import type { Metadata } from "next";

/**
 * Fallback metadata for a model page.
 *
 * Deliberately static. Generating a per-model title server-side would mean
 * `generateMetadata` fetching the API during rendering — which turns every
 * model page into a hard dependency on the backend being reachable at build
 * and request time, and produces a 500 rather than a page when it isn't.
 *
 * The page instead sets `document.title` once the model has loaded. That's a
 * legitimate trade for a client-rendered dashboard: crawlers get a sensible
 * generic title, and a person gets the model name in their tab.
 */
export const metadata: Metadata = {
  title: "Model detail",
  description:
    "Governance scorecard, lifecycle stage, measurement history, data lineage " +
    "and full audit trail for a registered model.",
};

export default function ModelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
