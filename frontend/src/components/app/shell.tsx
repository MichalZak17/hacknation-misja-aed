"use client";

import {
  BookOpenIcon,
  BracesIcon,
  CopyCheckIcon,
  DatabaseZapIcon,
  DownloadIcon,
  InboxIcon,
  LayoutDashboardIcon,
  LogOutIcon,
  MapPinIcon,
  PlugZapIcon,
  SparklesIcon,
} from "lucide-react";

import { useAuth } from "@/components/app/auth";
import { AppFrame, type NavItem } from "@/components/app/nav-bar";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, reportsApi } from "@/lib/api";
import { DOCS_ENABLED } from "@/lib/features";
import { useApi } from "@/lib/use-api";

type AdminNavItem = Omit<NavItem, "badge"> & { badge?: "pending_matches" | "new_reports" };

const NAV: AdminNavItem[] = [
  { href: "/panel", label: "Przegląd", icon: LayoutDashboardIcon },
  { href: "/integrations", label: "Integracje", icon: PlugZapIcon },
  { href: "/ai", label: "Klasyfikacja AI", short: "AI", icon: SparklesIcon },
  { href: "/devices", label: "Urządzenia", icon: DatabaseZapIcon },
  { href: "/map", label: "Mapa", icon: MapPinIcon },
  { href: "/matches", label: "Duplikaty", icon: CopyCheckIcon, badge: "pending_matches" },
  { href: "/zgloszenia", label: "Zgłoszenia", icon: InboxIcon, badge: "new_reports" },
  { href: "/export", label: "Eksport", icon: DownloadIcon },
  ...(DOCS_ENABLED ? [{ href: "/docs", label: "Dokumentacja", short: "Docs", icon: BookOpenIcon }] : []),
  { href: "/developers", label: "API", icon: BracesIcon },
];

type Counts = Partial<Record<NonNullable<AdminNavItem["badge"]>, number>>;

/** Fetched once in the shell, so a nav that remounts on navigation keeps its badges instead of flashing them. */
function useCounts(): Counts {
  const stats = useApi("stats", api.stats, { interval: 60_000 });
  const reports = useApi("reports:nav", () => reportsApi.list({ status: "new", limit: 1 }), { interval: 60_000 });
  return { pending_matches: stats.data?.pending_matches, new_reports: reports.data?.counts.new };
}

/** Who is signed in, with the one thing you do from there. Replaces a loose address and a button in the bar. */
function AccountMenu() {
  const { email, logout } = useAuth();
  const initial = (email.trim()[0] ?? "?").toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2 px-1.5" aria-label={`Konto: ${email || "…"}`}>
          <span
            aria-hidden
            className="font-display flex size-6 items-center justify-center bg-primary text-base leading-none text-primary-foreground"
          >
            {initial}
          </span>
          <span className="type-caption hidden max-w-40 truncate text-muted-foreground 2xl:inline">{email}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="type-caption text-subtle-foreground">Zalogowano jako</span>
          <span className="type-body truncate font-medium text-foreground">{email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => void logout()}>
          <LogOutIcon aria-hidden />
          Wyloguj
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** The admin frame: the shared app frame with the panel's destinations and the account. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const counts = useCounts();
  const items = NAV.map((item) => ({ ...item, badge: item.badge ? counts[item.badge] : undefined }));
  return (
    <AppFrame
      items={items}
      brandHref="/panel"
      brandLabel="Misja AED — przegląd"
      navLabel="Główna nawigacja"
      desktopFrom="xl"
      actions={
        <>
          <ThemeToggle />
          <span aria-hidden className="mx-1 hidden h-5 w-px bg-border sm:block" />
          <AccountMenu />
        </>
      }
    >
      <main id="main" className="mx-auto w-full max-w-page flex-1 px-4 py-6 md:px-6 2xl:px-10 md:py-8">
        {children}
      </main>
    </AppFrame>
  );
}
