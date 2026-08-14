import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Data handling",
  description:
    "What this tool does with uploaded files, what it stores, and what it sends " +
    "to third parties. Short, because it does very little.",
};

/**
 * A data-handling note rather than a boilerplate privacy policy.
 *
 * Most privacy pages on portfolio projects are copied from a generator and
 * describe tracking the site doesn't use and data it doesn't collect, which is
 * worse than having none: it's a page of claims nobody checked. This one
 * describes what the code actually does, which is short, because it does very
 * little.
 *
 * It exists at all because the assessment page accepts file uploads. Any tool
 * that takes a file owes the person an answer to "where did that go".
 */
export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-8 py-10">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 transition hover:text-slate-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to portfolio
      </Link>

      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          Data handling
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          What this tool does with what you give it. It is short because the
          tool does very little, and everything below describes behaviour you
          can verify in the source rather than promises.
        </p>
      </div>

      <Section title="Files you upload">
        <p>
          The assessment page accepts a CSV so it can compute statistics on it.
          The file is read into memory, analysed, and discarded when the request
          finishes. It is never written to disk, never stored in the database,
          and never sent anywhere else.
        </p>
        <p>
          Only aggregate results come back: row counts, missing-value shares,
          class balance, column names, distribution-shift scores, and the first
          few rows for display. The file itself does not persist beyond the
          request that carried it.
        </p>
        <p className="text-slate-500">
          Implementation: <code className="font-mono">app/api/routes.py</code>,{" "}
          <code className="font-mono">assess_dataset</code>.
        </p>
      </Section>

      <Section title="Models you describe">
        <p>
          Descriptions entered on the assessment page are evaluated and returned.
          Nothing is written to the registry. Assessing a hypothetical model
          should not put it in the inventory, and someone weighing options
          should not leave a trail of half-formed proposals behind.
        </p>
      </Section>

      <Section title="Analytics and tracking">
        <p>
          There are no analytics scripts, tracking pixels, fingerprinting, or
          advertising embeds. Supabase Auth uses session cookies only to keep
          approved users signed in and to attach a verified identity to actions.
        </p>
      </Section>

      <Section title="Accounts and authentication">
        <p>
          Account identity and session data are handled by Supabase Auth. The
          registry API receives a short-lived signed access token and records
          the verified account identity against governance decisions; passwords
          are never sent to or stored by this application.
        </p>
      </Section>

      <Section title="Data the site fetches">
        <p>
          The registry holds model metadata, governance scores, approval history
          and lineage. The FX models additionally read live market data from
          public APIs: European Central Bank reference rates, and 1-minute
          currency quotes from a commercial market-data provider. Those requests
          are made by the backend, not by your browser.
        </p>
        <p>
          None of it is personal data. The credit datasets are either synthetic
          or already-public anonymised research sets, described per model on the
          relevant page.
        </p>
      </Section>

      <Section title="What this is">
        <p>
          A portfolio project demonstrating model risk management practice, not
          a commercial service. It stores governance records but delegates
          account credentials and sessions to Supabase Auth. It sends no
          marketing email and runs no behavioural analytics.
        </p>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel p-5">
      <h2 className="text-sm font-semibold text-white">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-slate-400">
        {children}
      </div>
    </section>
  );
}
