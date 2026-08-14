"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { LockKeyhole } from "lucide-react";

import { Logo } from "@/components/Logo";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-[65vh]" />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(searchParams.get("error") ?? "");

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    if (signInError) {
      setError(signInError.message);
      setBusy(false);
      return;
    }

    const requested = searchParams.get("next");
    const next = requested?.startsWith("/") && !requested.startsWith("//")
      ? requested
      : "/";
    router.replace(next);
    router.refresh();
  }

  return (
    <div className="mx-auto grid min-h-[65vh] max-w-md place-items-center py-10">
      <section className="panel w-full p-7">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-sky-500/12 text-sky-300 ring-1 ring-inset ring-sky-400/25">
            <Logo size={23} />
          </span>
          <div>
            <h1 className="text-lg font-semibold text-white">Secure registry access</h1>
            <p className="mt-0.5 text-xs text-slate-500">
              Sign in with your approved governance identity.
            </p>
          </div>
        </div>

        <form onSubmit={signIn} className="mt-7 space-y-4">
          <div>
            <label htmlFor="email" className="label mb-2 block">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="field"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="label mb-2 block">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="field"
              placeholder="Your password"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-3 py-2 text-xs text-rose-200">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full justify-center">
            <LockKeyhole className="h-4 w-4" />
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-slate-600">
          Need an account?{" "}
          <Link href="/signup" className="text-sky-300 transition hover:text-sky-200">
            Create one securely with Supabase
          </Link>
          . New accounts begin with read-only access.
        </p>
      </section>
    </div>
  );
}
