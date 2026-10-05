import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "My Teams — Cohort Shuffle",
  description: "Your full team history across all activities and cohorts.",
};

export default function TeamsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
