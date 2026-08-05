import { Loader2, PlugZap } from "lucide-react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-24 text-sm text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

/**
 * The most common failure in this app by far is "the FastAPI server isn't
 * running", so that case gets a specific, actionable message rather than a
 * generic error toast.
 */
export function ErrorState({ message }: { message: string }) {
  const looksLikeConnection = message.includes("Could not reach the API");

  return (
    <div className="panel mx-auto mt-10 max-w-2xl p-8">
      <div className="flex items-start gap-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-rose-500/10 ring-1 ring-inset ring-rose-400/25">
          <PlugZap className="h-5 w-5 text-rose-300" />
        </span>
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-white">
            {looksLikeConnection ? "Can't reach the backend" : "Something went wrong"}
          </h2>
          <p className="text-sm leading-relaxed text-slate-400">{message}</p>
          {looksLikeConnection && (
            <div className="rounded-lg border border-white/10 bg-ink-900/60 p-4">
              <p className="mb-2 text-xs text-slate-500">
                Start the API in a separate terminal, from the project root:
              </p>
              <code className="block font-mono text-xs text-sky-300">
                python -m uvicorn app.main:app --reload
              </code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-lg border border-dashed border-white/10 px-4 py-6 text-center text-sm text-slate-500">
      {children}
    </p>
  );
}
