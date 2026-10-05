// Shown instantly by Next.js while teams/page.tsx is loading.

export default function TeamsLoading() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="h-7 w-28 animate-pulse rounded-md bg-muted" />
        <div className="h-4 w-52 animate-pulse rounded-md bg-muted" />
      </div>

      {/* Stats row */}
      <div className="flex gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border bg-card px-4 py-3 text-center"
          >
            <div className="mx-auto h-7 w-8 animate-pulse rounded bg-muted" />
            <div className="mx-auto mt-1 h-3 w-14 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>

      {/* Team card skeletons */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card">
            <div className="flex justify-between gap-3 p-4">
              <div className="flex-1 space-y-2">
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                <div className="h-3 w-28 animate-pulse rounded bg-muted" />
                <div className="h-3 w-20 animate-pulse rounded bg-muted" />
              </div>
              <div className="space-y-1.5">
                <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
                <div className="h-3 w-12 animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="border-t px-4 py-2">
              <div className="h-4 w-32 animate-pulse rounded-full bg-muted" />
            </div>
            <div className="border-t px-4 py-3">
              <div className="h-3.5 w-20 animate-pulse rounded bg-muted" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
