/**
 * Skeleton placeholders.
 *
 * Preferred over a spinner for anything that resolves into a known layout.
 * A spinner says "wait"; a skeleton says "here is what's arriving, and roughly
 * where it will be" — so the page doesn't jump when the data lands, and the
 * wait feels shorter even when it isn't.
 *
 * Shapes deliberately mirror the real components' proportions. A skeleton that
 * doesn't match what replaces it is worse than none: the layout still shifts,
 * and now you've also told a small lie about it.
 */

function Bar({ className = "" }: { className?: string }) {
  return (
    <div
      className={`shimmer rounded ${className}`}
      // Inherits the row's stagger where one is set, so the highlight sweeps
      // down a list instead of every placeholder pulsing together.
      style={{ animationDelay: "var(--shimmer-delay, 0ms)" }}
    />
  );
}

export function StatsSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="panel p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="w-full">
              <Bar className="h-2.5 w-24" />
              <Bar className="mt-4 h-9 w-16" />
            </div>
            <Bar className="h-9 w-9 shrink-0 rounded-lg" />
          </div>
          <Bar className="mt-4 h-2.5 w-32" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="panel overflow-hidden">
      <ul className="divide-y divide-white/[0.05]">
        {Array.from({ length: rows }).map((_, i) => (
          <li
            key={i}
            className="flex items-center justify-between gap-4 px-5 py-4"
            // Each row's shimmer starts slightly later, so the light travels
            // down the list rather than every row flashing in unison.
            style={{ ["--shimmer-delay" as string]: `${i * 90}ms` }}
          >
            <div className="min-w-0 flex-1">
              <Bar className="h-3.5 w-48 max-w-full" />
              <Bar className="mt-2.5 h-2.5 w-72 max-w-full" />
              <Bar className="mt-2 h-2 w-40 max-w-full" />
            </div>
            <div className="hidden items-center gap-3 sm:flex">
              <Bar className="h-6 w-20 rounded-full" />
              <Bar className="h-6 w-24 rounded-full" />
              <Bar className="h-5 w-10" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="panel p-6">
        <Bar className="h-8 w-72 max-w-full" />
        <Bar className="mt-4 h-3 w-96 max-w-full" />
        <div className="mt-5 flex gap-2">
          <Bar className="h-6 w-24 rounded-full" />
          <Bar className="h-6 w-28 rounded-full" />
          <Bar className="h-6 w-20 rounded-full" />
        </div>
        <div className="mt-7 grid gap-4 border-t border-white/[0.06] pt-5 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i}>
              <Bar className="h-2.5 w-20" />
              <Bar className="mt-2.5 h-3.5 w-32" />
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="panel space-y-4 p-5">
            <Bar className="h-3.5 w-40" />
            <Bar className="h-2.5 w-64 max-w-full" />
            {[0, 1, 2, 3, 4].map((j) => (
              <div key={j}>
                <Bar className="h-2.5 w-28" />
                <Bar className="mt-2 h-1.5 w-full rounded-full" />
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="panel p-5">
        <Bar className="h-3.5 w-48" />
        <Bar className="mt-5 h-64 w-full rounded-lg" />
      </div>
    </div>
  );
}
