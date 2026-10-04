import { AppShell } from "@/components/layout/AppShell";
import { CohortProvider } from "@/contexts/CohortContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <CohortProvider>
      <AppShell>{children}</AppShell>
    </CohortProvider>
  );
}
