import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard — Cohort Shuffle",
  description: "Your upcoming activities and recent teams at a glance.",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
