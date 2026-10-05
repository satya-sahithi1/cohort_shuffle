"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Shuffle,
  LayoutDashboard,
  CalendarDays,
  Users,
  Settings,
  Menu,
  X,
} from "lucide-react";
import { CohortSwitcher } from "./CohortSwitcher";
import { UserMenu } from "./UserMenu";
import { cn } from "@/lib/utils";
import { useCohort } from "@/contexts/CohortContext";

// ─── Nav link definition ──────────────────────────────────────────────────────

interface NavLink {
  href: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
  /** Use exact match for active state instead of prefix match */
  exact?: boolean;
}

const NAV_LINKS: NavLink[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
    exact: true, // /dashboard only, never /dashboard/something
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

// ─── Active link check ────────────────────────────────────────────────────────

function isActive(pathname: string, link: NavLink): boolean {
  if (link.exact) return pathname === link.href;
  return pathname === link.href || pathname.startsWith(link.href + "/");
}

// ─── Desktop nav link ─────────────────────────────────────────────────────────

function DesktopNavLink({
  link,
  pathname,
}: {
  link: NavLink;
  pathname: string;
}) {
  const active = isActive(pathname, link);
  return (
    <Link
      href={link.href}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      )}
      aria-current={active ? "page" : undefined}
    >
      {link.icon}
      {link.label}
    </Link>
  );
}

// ─── Mobile nav sheet ─────────────────────────────────────────────────────────

function MobileNav({
  open,
  onClose,
  links,
  pathname,
}: {
  open: boolean;
  onClose: () => void;
  links: NavLink[];
  pathname: string;
}) {
  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-50 bg-black/40 transition-opacity duration-200 md:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />

      {/* Slide-in panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 bg-background shadow-xl transition-transform duration-200 ease-in-out md:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Panel header */}
        <div className="flex h-14 items-center justify-between border-b px-4">
          <Link
            href="/dashboard"
            onClick={onClose}
            className="flex items-center gap-2 font-semibold"
          >
            <Shuffle className="h-5 w-5 text-primary" />
            Cohort Shuffle
          </Link>
          <button
            onClick={onClose}
            aria-label="Close navigation"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex flex-col gap-1 p-3" aria-label="Mobile navigation">
          {links.map((link) => {
            const active = isActive(pathname, link);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={onClose}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}

// ─── TopNav ───────────────────────────────────────────────────────────────────

export function TopNav() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { activeCohort } = useCohort();
  const isAdmin = session?.user?.role === "admin";

  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile nav whenever the route changes
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const visibleLinks = NAV_LINKS.filter(
    (link) => !link.adminOnly || isAdmin
  );

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
            className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Logo */}
          <Link
            href="/dashboard"
            className="flex items-center gap-2 font-semibold text-foreground"
          >
            <Shuffle className="h-5 w-5 text-primary" />
            <span className="hidden sm:inline">Cohort Shuffle</span>
          </Link>

          {/* Desktop nav links */}
          <nav
            className="hidden md:flex items-center gap-1"
            aria-label="Main navigation"
          >
            {visibleLinks.map((link) => (
              <DesktopNavLink key={link.href} link={link} pathname={pathname} />
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

      {/* Mobile nav slide-out */}
      <MobileNav
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        links={visibleLinks}
        pathname={pathname}
      />
    </>
  );
}
