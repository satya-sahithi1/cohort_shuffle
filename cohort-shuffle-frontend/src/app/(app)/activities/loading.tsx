// Shown instantly by Next.js while activities/page.tsx is loading.
// Mimics the real page layout to avoid layout shift.

export default function ActivitiesLoading() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-7 w-32 animate-pulse rounded-md bg-muted" />
          <div className="h-4 w-48 animate-pulse rounded-md bg-muted" />
        </div>
        <div className="h-8 w-28 animate-pulse rounded-md bg-muted" />
      </div>

      {/* Section label */}
      <div className="h-4 w-40 animate-pulse rounded-md bg-muted" />

      {/* Card skeletons */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="flex flex-col gap-3 rounded-xl border bg-card p-5"
          >
            <div className="flex justify-between gap-2">
              <div className="h-5 w-40 animate-pulse rounded bg-muted" />
              <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
            </div>
            <div className="space-y-2">
              <div className="h-3.5 w-36 animate-pulse rounded bg-muted" />
              <div className="h-3.5 w-24 animate-pulse rounded bg-muted" />
              <div className="h-3.5 w-28 animate-pulse rounded bg-muted" />
            </div>
            <div className="mt-auto flex gap-2 pt-2">
              <div className="h-7 flex-1 animate-pulse rounded-md bg-muted" />
              <div className="h-7 w-20 animate-pulse rounded-md bg-muted" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
