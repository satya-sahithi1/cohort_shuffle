"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { Shuffle, LayoutDashboard, CalendarDays, Users, Settings } from "lucide-react";
import { CohortSwitcher } from "./CohortSwitcher";
import { UserMenu } from "./UserMenu";
import { cn } from "@/lib/utils";
import { useCohort } from "@/contexts/CohortContext";

interface NavLink {
  href: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV_LINKS: NavLink[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    href: "/activities",
    label: "Activities",
    icon: <CalendarDays className="h-4 w-4" />,
  },
  {
    href: "/teams",
    label: "My Teams",
    icon: <Users className="h-4 w-4" />,
  },
  {
    href: "/admin",
    label: "Manage",
    icon: <Settings className="h-4 w-4" />,
    adminOnly: true,
  },
];

export function TopNav() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { activeCohort } = useCohort();
  const isAdmin = session?.user?.role === "admin";

  const visibleLinks = NAV_LINKS.filter(
    (link) => !link.adminOnly || isAdmin
  );

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link
          href="/dashboard"
          className="flex items-center gap-2 font-semibold text-foreground"
        >
          <Shuffle className="h-5 w-5 text-primary" />
          <span className="hidden sm:inline">Cohort Shuffle</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {visibleLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                pathname.startsWith(link.href)
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Cohort switcher */}
        {activeCohort && <CohortSwitcher />}

        {/* User menu */}
        <UserMenu />
      </div>
    </header>
  );
}
