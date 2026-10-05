import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "New Activity — Cohort Shuffle",
  description: "Create a new activity for your cohort.",
};

export default function NewActivityLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
