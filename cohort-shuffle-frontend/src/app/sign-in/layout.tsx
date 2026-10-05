import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign In — Cohort Shuffle",
  description: "Sign in with Google to access your activities and teams.",
};

export default function SignInLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
