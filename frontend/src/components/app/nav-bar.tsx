"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";
import { EllipsisIcon, type LucideIcon } from "lucide-react";

import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

export type NavItem = {
  href: string;
  label: string;
  /** A shorter label for the bottom tab bar on phones and the top tabs below 2xl (defaults to `label`). */
  short?: string;
  icon: LucideIcon;
  /** Work waiting for a person, shown as a count next to the item. */
  badge?: number;
};

/** Where the top tabs take over from the bottom tab bar. Literal classes, so Tailwind sees them. */
const BREAKPOINT = {
  lg: { desktop: "hidden lg:block", mobile: "lg:hidden", pad: "pb-[calc(4rem+env(safe-area-inset-bottom))] lg:pb-0" },
  xl: { desktop: "hidden xl:block", mobile: "xl:hidden", pad: "pb-[calc(4rem+env(safe-area-inset-bottom))] xl:pb-0" },
} as const;

/** A phone's bottom bar holds this many slots; with more items the last slot becomes "Więcej". */
const TAB_SLOTS = 5;

const focusRing = "outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring";

function isActive(pathname: string | null, href: string) {
  if (!pathname) return false;
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** A hard-edged tile, so it reads as a count and not as a status dot. */
function Count({ value, className }: { value: number | undefined; className?: string }) {
  if (!value) return null;
  return (
    <span
      className={cn(
        "type-micro inline-flex h-4 min-w-4 items-center justify-center bg-caution px-1 text-caution-foreground tabular-nums",
        className,
      )}
    >
      <span aria-hidden>{value > 99 ? "99+" : value}</span>
      <span className="sr-only">, do przejrzenia: {value}</span>
    </span>
  );
}

/** Desktop: tabs that fill the bar's height; the current one carries a crimson bar on the bar's bottom edge. */
function TopTabs({ items, pathname }: { items: NavItem[]; pathname: string | null }) {
  return (
    <ul className="flex h-full items-stretch">
      {items.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <li key={item.href} className="flex">
            <Link
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "type-body relative flex items-center gap-2 px-2.5 font-medium whitespace-nowrap transition-colors 2xl:px-3",
                focusRing,
                active ? "text-foreground" : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <item.icon aria-hidden className={cn("size-4", active ? "text-hn-crimson" : "text-subtle-foreground")} />
              {item.short && item.short !== item.label ? (
                <>
                  {/* Laptop widths: the short label keeps every tab in the bar; screen readers always get the full one */}
                  <span aria-hidden className="2xl:hidden">
                    {item.short}
                  </span>
                  <span className="sr-only 2xl:not-sr-only">{item.label}</span>
                </>
              ) : (
                item.label
              )}
              <Count value={item.badge} />
              {active ? <span aria-hidden className="absolute inset-x-3 -bottom-px h-[3px] bg-hn-crimson" /> : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

const tabClass = (active: boolean) =>
  cn(
    "relative flex h-16 w-full flex-col items-center justify-center gap-1 px-1 text-[0.6875rem] leading-none font-semibold transition-colors",
    focusRing,
    active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
  );

function TabIcon({ icon: Icon, active, badge }: { icon: LucideIcon; active: boolean; badge?: number }) {
  return (
    <span className="relative">
      <Icon aria-hidden className={cn("size-6", active ? "text-hn-crimson" : "text-subtle-foreground")} />
      <Count value={badge} className="absolute -top-1.5 left-4" />
    </span>
  );
}

/** Phones and tablets: a tab bar along the bottom edge, in thumb reach; overflow goes into a "Więcej" sheet. */
function BottomTabs({ items, pathname, title }: { items: NavItem[]; pathname: string | null; title: string }) {
  const [open, setOpen] = useState(false);
  const overflow = items.length > TAB_SLOTS;
  const tabs = overflow ? items.slice(0, TAB_SLOTS - 1) : items;
  const rest = overflow ? items.slice(TAB_SLOTS - 1) : [];
  const restActive = rest.some((item) => isActive(pathname, item.href));
  const restBadge = rest.reduce((sum, item) => sum + (item.badge ?? 0), 0) || undefined;

  return (
    <ul className="flex">
      {tabs.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <li key={item.href} className="min-w-0 flex-1">
            <Link href={item.href} aria-current={active ? "page" : undefined} className={tabClass(active)}>
              {active ? <span aria-hidden className="absolute inset-x-3 top-0 h-[3px] bg-hn-crimson" /> : null}
              <TabIcon icon={item.icon} active={active} badge={item.badge} />
              <span className="max-w-full truncate">{item.short ?? item.label}</span>
            </Link>
          </li>
        );
      })}
      {overflow ? (
        <li className="min-w-0 flex-1">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button type="button" className={tabClass(restActive)} aria-current={restActive ? "page" : undefined}>
                {restActive ? <span aria-hidden className="absolute inset-x-3 top-0 h-[3px] bg-hn-crimson" /> : null}
                <TabIcon icon={EllipsisIcon} active={restActive} badge={restBadge} />
                <span>Więcej</span>
              </button>
            </SheetTrigger>
            <SheetContent side="bottom" className="gap-0 p-0 pb-[env(safe-area-inset-bottom)]" showCloseButton>
              <div className="border-b border-border px-4 py-4">
                <SheetTitle className="font-display text-[1.75rem] leading-none tracking-[0.02em] text-hn-heading uppercase">
                  {title}
                </SheetTitle>
                <SheetDescription className="sr-only">Pozostałe strony</SheetDescription>
              </div>
              <ul className="py-2">
                {rest.map((item) => {
                  const active = isActive(pathname, item.href);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "type-lead relative flex min-h-12 items-center gap-3 px-4 font-medium transition-colors",
                          focusRing,
                          active ? "bg-selected text-foreground" : "text-muted-foreground hover:bg-accent hover:text-foreground",
                        )}
                      >
                        {active ? <span aria-hidden className="absolute inset-y-0 left-0 w-[3px] bg-hn-crimson" /> : null}
                        <item.icon aria-hidden className={cn("size-5", active ? "text-hn-crimson" : "text-subtle-foreground")} />
                        {item.label}
                        <Count value={item.badge} className="ml-auto" />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </SheetContent>
          </Sheet>
        </li>
      ) : null}
    </ul>
  );
}

function WithPathname({ children }: { children: (pathname: string | null) => React.ReactNode }) {
  return children(usePathname());
}

/**
 * The frame every page shares, public and admin: a top bar with the brand, the destinations as tabs and the actions;
 * on phones the destinations move to a tab bar along the bottom edge and the top bar keeps only brand and actions.
 */
export function AppFrame({
  items,
  brandHref,
  brandLabel,
  navLabel,
  actions,
  desktopFrom = "lg",
  children,
}: {
  items: NavItem[];
  brandHref: string;
  brandLabel: string;
  navLabel: string;
  actions?: React.ReactNode;
  desktopFrom?: keyof typeof BREAKPOINT;
  children: React.ReactNode;
}) {
  const bp = BREAKPOINT[desktopFrom];
  return (
    <div className={cn("flex min-h-svh flex-col bg-frame", bp.pad)}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-background focus:px-3 focus:py-2"
      >
        Przejdź do treści
      </a>
      <header className="sticky top-0 z-40 border-b border-border bg-background pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex h-14 max-w-page items-center gap-3 pr-[max(0.5rem,env(safe-area-inset-right))] pl-[max(1rem,env(safe-area-inset-left))] md:px-6 lg:gap-4 2xl:gap-6 2xl:px-10">
          <Link href={brandHref} aria-label={brandLabel} className={cn("flex h-14 shrink-0 items-center gap-2.5", focusRing)}>
            <span aria-hidden className="size-2.5 bg-hn-crimson" />
            <span className="font-display text-[1.75rem] leading-none tracking-[0.02em] text-hn-heading uppercase">
              Misja AED
            </span>
          </Link>
          <nav aria-label={navLabel} className={cn("h-full", bp.desktop)}>
            <Suspense fallback={<TopTabs items={items} pathname={null} />}>
              <WithPathname>{(pathname) => <TopTabs items={items} pathname={pathname} />}</WithPathname>
            </Suspense>
          </nav>
          <div className="ml-auto flex items-center gap-1">{actions}</div>
        </div>
      </header>
      {children}
      <nav
        aria-label={navLabel}
        className={cn(
          "fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)]",
          bp.mobile,
        )}
      >
        <Suspense fallback={<BottomTabs items={items} pathname={null} title="Misja AED" />}>
          <WithPathname>{(pathname) => <BottomTabs items={items} pathname={pathname} title="Misja AED" />}</WithPathname>
        </Suspense>
      </nav>
    </div>
  );
}
