import type { Metadata } from "next";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Model Governance Registry",
  description:
    "Risk-tiered approval, drift and fairness monitoring, and a full audit trail for a bank's AI model portfolio — aligned to RBI's 2026 draft Model Risk Management guidance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans text-slate-200 antialiased">
        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
            <Link href="/" className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-sky-500/15 ring-1 ring-inset ring-sky-400/25">
                <ShieldCheck className="h-5 w-5 text-sky-300" />
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

            <a
              href="https://www.rbi.org.in"
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-full border border-white/10 px-3 py-1.5 text-[11px] text-slate-400 transition hover:border-white/20 hover:text-slate-200 sm:block"
            >
              Aligned to RBI draft MRM guidance, 2026
            </a>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-5 pb-24 pt-8 sm:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
