import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin — Cohort Shuffle",
  description: "Manage activities, cohort members, and settings.",
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
