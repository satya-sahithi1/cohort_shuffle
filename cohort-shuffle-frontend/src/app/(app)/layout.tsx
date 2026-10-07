import { AppShell } from "@/components/layout/AppShell";
import { CohortProvider } from "@/contexts/CohortContext";
import { ToastProvider } from "@/contexts/ToastContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <CohortProvider>
      <ToastProvider>
        <AppShell>{children}</AppShell>
      </ToastProvider>
    </CohortProvider>
  );
}
