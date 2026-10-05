import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Join a Cohort — Cohort Shuffle",
  description: "Join a cohort to start working with your classmates.",
};

export default function JoinLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
