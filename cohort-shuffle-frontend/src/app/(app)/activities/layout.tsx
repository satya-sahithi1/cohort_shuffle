import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Activities — Cohort Shuffle",
  description: "Browse and register for activities in your cohort.",
};

export default function ActivitiesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
