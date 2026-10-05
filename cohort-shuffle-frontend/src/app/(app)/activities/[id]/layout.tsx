import type { Metadata } from "next";

// Dynamic titles require generateMetadata. Since the page is a client
// component we can't fetch the activity name server-side without an extra
// server request, so we set a sensible default here. The browser <title>
// will show this while the page loads.
export const metadata: Metadata = {
  title: "Activity — Cohort Shuffle",
  description: "View activity details, register, and see your team.",
};

export default function ActivityDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
