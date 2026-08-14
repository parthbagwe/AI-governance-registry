"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { CheckCircle2, UserPlus } from "lucide-react";

import { Logo } from "@/components/Logo";
import { createClient } from "@/lib/supabase/client";

export default function SignUpPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(false);

  async function signUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setBusy(true);
    const supabase = createClient();
    const callback = new URL("/auth/callback", window.location.origin);
    callback.searchParams.set("next", "/");

    const { data, error: signUpError } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        emailRedirectTo: callback.toString(),
        data: { full_name: fullName.trim() },
      },
    });

    if (signUpError) {
      setError(signUpError.message);
      setBusy(false);
      return;
    }

    if (data.session) {
      window.location.assign("/");
      return;
    }

    setCreated(true);
    setBusy(false);
  }

  if (created) {
    return (
      <div className="mx-auto grid min-h-[65vh] max-w-md place-items-center py-10">
        <section className="panel w-full p-7 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-300" />
          <h1 className="mt-4 text-lg font-semibold text-white">Check your email</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Supabase sent a confirmation link to <span className="text-slate-200">{email}</span>.
            Confirm it, then sign in. Your account starts with viewer access.
          </p>
          <Link href="/login" className="btn-primary mt-6 w-full">
            Go to sign in
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto grid min-h-[65vh] max-w-md place-items-center py-10">
      <section className="panel w-full p-7">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-sky-500/12 text-sky-300 ring-1 ring-inset ring-sky-400/25">
            <Logo size={23} />
          </span>
          <div>
            <h1 className="text-lg font-semibold text-white">Create registry account</h1>
            <p className="mt-0.5 text-xs text-slate-500">
              Identity and passwords are managed by Supabase Auth.
            </p>
          </div>
        </div>

        <form onSubmit={signUp} className="mt-7 space-y-4">
          <div>
            <label htmlFor="full-name" className="label mb-2 block">Full name</label>
            <input id="full-name" autoComplete="name" required value={fullName}
              onChange={(event) => setFullName(event.target.value)} className="field"
              placeholder="Your name" />
          </div>
          <div>
            <label htmlFor="signup-email" className="label mb-2 block">Work email</label>
            <input id="signup-email" type="email" autoComplete="email" required value={email}
              onChange={(event) => setEmail(event.target.value)} className="field"
              placeholder="you@example.com" />
          </div>
          <div>
            <label htmlFor="signup-password" className="label mb-2 block">Password</label>
            <input id="signup-password" type="password" autoComplete="new-password" required
              minLength={8} value={password} onChange={(event) => setPassword(event.target.value)}
              className="field" placeholder="At least 8 characters" />
          </div>
          <div>
            <label htmlFor="confirm-password" className="label mb-2 block">Confirm password</label>
            <input id="confirm-password" type="password" autoComplete="new-password" required
              minLength={8} value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)} className="field"
              placeholder="Repeat your password" />
          </div>

          {error && (
            <p className="rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-3 py-2 text-xs text-rose-200">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            <UserPlus className="h-4 w-4" />
            {busy ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-slate-600">
          Already registered?{" "}
          <Link href="/login" className="text-sky-300 transition hover:text-sky-200">Sign in</Link>.
          By continuing, you acknowledge the <Link href="/privacy" className="underline">privacy notice</Link>.
        </p>
      </section>
    </div>
  );
}
