import Link from "next/link";
import { ArrowLeftIcon, ArrowRightIcon, PencilLineIcon } from "lucide-react";

import { DocBody } from "@/components/docs/mdx";
import { REPO_BLOB_URL, getDoc, listDocs } from "@/lib/docs";

/** One documentation page: the article, "on this page" on wide screens, and the neighbours in the menu order. */
export async function DocPage({ slug }: { slug: string[] }) {
  const doc = await getDoc(slug);
  if (!doc) return null;
  const pages = await listDocs();
  const i = pages.findIndex((d) => d.href === doc.meta.href);
  const prev = pages[i - 1];
  const next = pages[i + 1];

  return (
    <div className={`grid min-w-0 gap-8 ${doc.toc.length > 1 ? "xl:grid-cols-[minmax(0,1fr)_13rem]" : ""}`}>
      <article className="min-w-0 bg-background px-5 py-6 ring-1 ring-border md:px-8 md:py-8">
        <DocBody source={doc.source} meta={doc.meta} pages={pages} />

        <nav aria-label="Sąsiednie dokumenty" className="mt-12 grid gap-3 border-t border-border pt-6 sm:grid-cols-2">
          {prev ? (
            <Link href={prev.href} rel="prev" className="type-body group flex items-center gap-2 text-muted-foreground hover:text-foreground">
              <ArrowLeftIcon aria-hidden className="size-4 shrink-0" />
              <span className="min-w-0">
                <span className="type-caption block text-subtle-foreground">Poprzedni</span>
                <span className="block truncate font-medium group-hover:underline">{prev.nav}</span>
              </span>
            </Link>
          ) : (
            <span />
          )}
          {next ? (
            <Link
              href={next.href}
              rel="next"
              className="type-body group flex items-center justify-end gap-2 text-right text-muted-foreground hover:text-foreground"
            >
              <span className="min-w-0">
                <span className="type-caption block text-subtle-foreground">Następny</span>
                <span className="block truncate font-medium group-hover:underline">{next.nav}</span>
              </span>
              <ArrowRightIcon aria-hidden className="size-4 shrink-0" />
            </Link>
          ) : null}
        </nav>

        <p className="type-caption mt-6">
          <a
            href={`${REPO_BLOB_URL}/docs/${doc.meta.file}`}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1.5 text-subtle-foreground hover:text-foreground hover:underline"
          >
            <PencilLineIcon aria-hidden className="size-3.5" />
            Popraw tę stronę w repozytorium
            <span className="sr-only"> (otwiera się w nowej karcie)</span>
          </a>
        </p>
      </article>

      {doc.toc.length > 1 ? (
        <nav aria-label="Na tej stronie" className="hidden xl:sticky xl:top-20 xl:block xl:max-h-[calc(100svh-6.5rem)] xl:self-start xl:overflow-y-auto">
          <h2 className="type-label mb-2 text-subtle-foreground">Na tej stronie</h2>
          <ul className="border-l border-border">
            {doc.toc.map((t) => (
              <li key={t.id}>
                <a
                  href={`#${t.id}`}
                  className={
                    "type-caption block py-1 text-muted-foreground outline-none hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring " +
                    (t.level === 3 ? "pl-6" : "pl-3")
                  }
                >
                  {t.text}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </div>
  );
}
