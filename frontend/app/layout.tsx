import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { SmoothScroll } from "@/components/SmoothScroll";
import { Preloader } from "@/components/Preloader";
import { RouteTransition } from "@/components/RouteTransition";
import { AuthNav } from "@/components/AuthNav";
import "./globals.css";

// Falls back to localhost so a fresh clone builds without configuration. Set
// NEXT_PUBLIC_SITE_URL in Vercel — without an absolute base, Open Graph images
// resolve to relative paths that no social platform can fetch, and the link
// preview silently comes back blank.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

const DESCRIPTION =
  "A working model risk management layer for banking AI: risk-tiered approval gates, " +
  "an emergency kill switch, live drift monitoring on real market data, and an " +
  "append-only audit trail. Built against the RBI's 2026 draft Model Risk " +
  "Management guidance.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    // Pages set only their own name; the suffix is appended automatically, so
    // a browser tab reads "Assess a model · AI Model Governance Registry"
    // rather than every tab looking identical.
    default: "AI Model Governance Registry",
    template: "%s · AI Model Governance Registry",
  },
  description: DESCRIPTION,
  applicationName: "AI Model Governance Registry",
  authors: [{ name: "Parth Bagwe" }],
  keywords: [
    "model risk management",
    "AI governance",
    "RBI",
    "banking AI",
    "drift detection",
    "model registry",
    "MLOps",
  ],
  openGraph: {
    type: "website",
    siteName: "AI Model Governance Registry",
    title: "AI Model Governance Registry",
    description: DESCRIPTION,
    url: SITE_URL,
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Model Governance Registry",
    description: DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans text-slate-200 antialiased">
        <Preloader />
        <SmoothScroll />
        <RouteTransition />

        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
            <Link href="/" className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-sky-500/12 text-sky-300 ring-1 ring-inset ring-sky-400/25">
                <Logo size={20} />
              </span>
              <span className="leading-tight">
                <span className="block text-sm font-semibold text-white">
                  AI Model Governance Registry
                </span>
                <span className="block text-[11px] text-slate-500">
                  Model risk management for banking AI
                </span>
              </span>
            </Link>

            <nav className="flex items-center gap-1.5">
              <Link
                href="/"
                className="rounded-lg px-3 py-1.5 text-xs text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
              >
                Portfolio
              </Link>
              <Link
                href="/assess"
                className="rounded-lg px-3 py-1.5 text-xs text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
              >
                Assess a model
              </Link>
              <Link
                href="/methodology"
                className="hidden rounded-lg px-3 py-1.5 text-xs text-slate-400 transition hover:bg-white/5 hover:text-slate-200 sm:block"
              >
                Data & methods
              </Link>
              <span className="ml-1 hidden rounded-full border border-white/10 px-3 py-1.5 text-[11px] text-slate-500 lg:block">
                RBI draft MRM guidance, 2026
              </span>
              <AuthNav />
            </nav>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-5 pb-16 pt-8 sm:px-8">
          {children}
        </main>

        <footer className="mx-auto max-w-7xl px-5 pb-12 sm:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-6">
            <p className="text-[11px] text-slate-600">
              A portfolio project on model risk management for banking AI. Not a
              commercial service.
            </p>
            <div className="flex items-center gap-4">
              <Link
                href="/privacy"
                className="text-[11px] text-slate-500 transition hover:text-slate-300"
              >
                Data handling
              </Link>
              <Link
                href="/methodology"
                className="text-[11px] text-slate-500 transition hover:text-slate-300"
              >
                Data & methodology
              </Link>
              <a
                href="https://github.com/parthbagwe/AI-governance-registry"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-slate-500 transition hover:text-slate-300"
              >
                Source
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
