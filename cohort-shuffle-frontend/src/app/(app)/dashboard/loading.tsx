// Shown instantly by Next.js while dashboard/page.tsx is loading.

export default function DashboardLoading() {
  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div className="space-y-1.5">
        <div className="h-7 w-56 animate-pulse rounded-md bg-muted" />
        <div className="h-4 w-40 animate-pulse rounded-md bg-muted" />
      </div>

      {/* Open activities section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-5 w-32 animate-pulse rounded bg-muted" />
          <div className="h-7 w-24 animate-pulse rounded-md bg-muted" />
        </div>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="flex justify-between gap-3 rounded-lg border bg-card p-4"
            >
              <div className="flex-1 space-y-2">
                <div className="h-4 w-48 animate-pulse rounded bg-muted" />
                <div className="h-3 w-36 animate-pulse rounded bg-muted" />
                <div className="h-3 w-24 animate-pulse rounded bg-muted" />
              </div>
              <div className="h-5 w-20 animate-pulse rounded-full bg-muted" />
            </div>
          ))}
        </div>
      </div>

      {/* Recent teams section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-5 w-28 animate-pulse rounded bg-muted" />
          <div className="h-7 w-24 animate-pulse rounded-md bg-muted" />
        </div>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div
              key={i}
              className="flex justify-between gap-3 rounded-lg border bg-card p-4"
            >
              <div className="flex-1 space-y-2">
                <div className="h-4 w-44 animate-pulse rounded bg-muted" />
                <div className="h-3 w-32 animate-pulse rounded bg-muted" />
                <div className="h-3 w-40 animate-pulse rounded bg-muted" />
              </div>
              <div className="h-3 w-12 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
