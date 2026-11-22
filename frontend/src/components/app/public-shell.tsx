"use client";

import Link from "next/link";
import { BookOpenIcon, BracesIcon, DownloadIcon, MapPinIcon } from "lucide-react";

import { AppFrame, type NavItem } from "@/components/app/nav-bar";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import { DOCS_ENABLED } from "@/lib/features";

const NAV: NavItem[] = [
  { href: "/", label: "Znajdź AED", icon: MapPinIcon },
  { href: "/export", label: "Dane do pobrania", short: "Dane", icon: DownloadIcon },
  ...(DOCS_ENABLED ? [{ href: "/docs", label: "Dokumentacja", icon: BookOpenIcon }] : []),
  { href: "/developers", label: "API", icon: BracesIcon },
];

/** The public frame: brand to the citizen map, the public pages, and a way into the admin panel. */
export function PublicFrame({ children }: { children: React.ReactNode }) {
  return (
    <AppFrame
      items={NAV}
      brandHref="/"
      brandLabel="Misja AED — znajdź najbliższy defibrylator"
      navLabel="Strony publiczne"
      actions={
        <>
          <ThemeToggle />
          <span aria-hidden className="mx-1 hidden h-5 w-px bg-border sm:block" />
          <Button asChild variant="outline" size="sm">
            <Link href="/panel">
              <span className="sm:hidden">Panel</span>
              <span className="hidden sm:inline">Panel dysponenta</span>
            </Link>
          </Button>
        </>
      }
    >
      {children}
    </AppFrame>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="type-caption mx-auto flex max-w-page flex-col gap-2 px-4 py-4 text-subtle-foreground md:flex-row md:items-center md:justify-between md:px-6 2xl:px-10">
        <p>
          Misja AED · HackNation 2026 · zadanie Ministerstwa Cyfryzacji. Dane w formatach odczytywalnych maszynowo, do
          publikacji na{" "}
          <a href="https://dane.gov.pl" className="text-link hover:text-link-hover hover:underline">
            dane.gov.pl
          </a>
          . Mapa © współtwórcy OpenStreetMap.
        </p>
        <ul className="flex flex-wrap gap-x-4 gap-y-1">
          <li>
            <Link href="/zglos" className="inline-flex min-h-6 items-center text-link hover:text-link-hover hover:underline">
              Zgłoś AED lub błąd
            </Link>
          </li>
          <li>
            <Link href="/export" className="inline-flex min-h-6 items-center text-link hover:text-link-hover hover:underline">
              Otwarte dane
            </Link>
          </li>
          {DOCS_ENABLED ? (
            <li>
              <Link href="/docs" className="inline-flex min-h-6 items-center text-link hover:text-link-hover hover:underline">
                Dokumentacja
              </Link>
            </li>
          ) : null}
          <li>
            <Link href="/developers" className="inline-flex min-h-6 items-center text-link hover:text-link-hover hover:underline">
              API
            </Link>
          </li>
        </ul>
      </div>
    </footer>
  );
}

/** The frame for public pages (downloads and documentation): no session needed, a way into the admin panel. */
export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <PublicFrame>
      <main id="main" className="mx-auto w-full max-w-page flex-1 px-4 py-6 md:px-6 2xl:px-10 md:py-8">
        {children}
      </main>
      <PublicFooter />
    </PublicFrame>
  );
}
