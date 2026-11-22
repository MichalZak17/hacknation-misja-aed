"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

import type { DocGroup } from "@/lib/docs";
import { cn } from "@/lib/utils";

function Groups({ groups, pathname }: { groups: DocGroup[]; pathname: string | null }) {
  return (
    <div className="flex flex-col gap-5">
      {groups.map((group) => (
        <div key={group.title}>
          <h2 className="type-label mb-1 px-3 text-subtle-foreground">{group.title}</h2>
          <ul>
            {group.docs.map((doc) => {
              const active = pathname === doc.href;
              return (
                <li key={doc.href}>
                  <Link
                    href={doc.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "type-body relative block border-l-[3px] px-3 py-1.5 transition-colors outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
                      active
                        ? "border-hn-crimson bg-selected font-medium text-foreground"
                        : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
                    )}
                  >
                    {doc.nav}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

function Active({ groups }: { groups: DocGroup[] }) {
  const pathname = usePathname();
  const current = groups.flatMap((g) => g.docs).find((d) => d.href === pathname);
  return (
    <>
      {/* Phones: the list folds away, and the summary says where you are. */}
      <details className="group bg-background ring-1 ring-border lg:hidden">
        <summary className="type-body flex min-h-11 cursor-pointer items-center justify-between gap-2 px-3 font-medium outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring">
          <span className="truncate">{current?.nav ?? "Spis dokumentów"}</span>
          <span className="type-caption shrink-0 text-subtle-foreground group-open:hidden">Spis dokumentów</span>
          <span className="type-caption hidden shrink-0 text-subtle-foreground group-open:inline">Zwiń</span>
        </summary>
        <div className="border-t border-border py-3">
          <Groups groups={groups} pathname={pathname} />
        </div>
      </details>
      <div className="hidden lg:block">
        <Groups groups={groups} pathname={pathname} />
      </div>
    </>
  );
}

/** The documentation menu: grouped by folder, the current page marked with the brand's crimson edge. */
export function DocsNav({ groups }: { groups: DocGroup[] }) {
  return (
    <nav aria-label="Dokumentacja" className="lg:sticky lg:top-20 lg:max-h-[calc(100svh-6.5rem)] lg:self-start lg:overflow-y-auto">
      <Suspense fallback={null}>
        <Active groups={groups} />
      </Suspense>
    </nav>
  );
}
