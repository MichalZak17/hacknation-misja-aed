import path from "node:path";

import Link from "next/link";
import { evaluate } from "@mdx-js/mdx";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import type { MDXComponents } from "mdx/types";

import { AccentBar } from "@/components/brand";
import { DatasetFacts, DatasetMetadata, DictionaryDownloads, SchemaTable, SourcesTable } from "@/components/docs/live";
import { REPO_BLOB_URL, REPO_TREE_URL, type DocMeta } from "@/lib/docs";
import { cn } from "@/lib/utils";

const linkClass = "text-link underline underline-offset-2 hover:text-link-hover";

/** Where a link written in an .mdx file points on this site: another page, the repository, or off-site. */
function resolveHref(href: string, from: DocMeta, pages: Map<string, string>) {
  if (/^([a-z][a-z0-9+.-]*:|\/|#)/i.test(href)) return { href, kind: /^https?:/i.test(href) ? "external" : "local" } as const;
  const [target, hash = ""] = href.split("#");
  const rel = path.posix.normalize(path.posix.join(path.posix.dirname(from.file), target));
  const page = pages.get(rel);
  if (page) return { href: hash ? `${page}#${hash}` : page, kind: "page" } as const;
  // A file elsewhere in the repository (code, a README, a .md note): docs/ sits one level below the repository root.
  const repoPath = path.posix.join("docs", rel);
  const base = target.endsWith("/") || !path.posix.extname(target) ? REPO_TREE_URL : REPO_BLOB_URL;
  return { href: `${base}/${repoPath}${hash ? `#${hash}` : ""}`, kind: "external" } as const;
}

function Heading({ level, id, children }: { level: 1 | 2 | 3 | 4; id?: string; children?: React.ReactNode }) {
  const Tag = `h${level}` as const;
  const styles = {
    1: "type-h1 text-hn-heading",
    2: "type-h2 mt-12 border-t border-border pt-6 text-hn-heading",
    3: "type-h3 mt-8 text-hn-heading",
    4: "type-h4 mt-6 text-foreground",
  } as const;
  return (
    <>
      <Tag id={id} className={cn("scroll-mt-20", styles[level])}>
        {id && level > 1 ? (
          <a href={`#${id}`} className="outline-none hover:underline focus-visible:outline-2 focus-visible:outline-ring">
            {children}
          </a>
        ) : (
          children
        )}
      </Tag>
      {level === 1 ? <AccentBar className="mt-2 mb-6 w-[min(28rem,70%)]" /> : null}
    </>
  );
}

/** A short aside inside a page: `<Note>…</Note>`. */
function Note({ children }: { children: React.ReactNode }) {
  return <aside className="type-body my-6 border-l-[3px] border-hn-slate bg-canvas px-4 py-3 dark:border-hn-cyan">{children}</aside>;
}

function elements(from: DocMeta, pages: Map<string, string>): MDXComponents {
  return {
    h1: (p) => <Heading level={1} {...p} />,
    h2: (p) => <Heading level={2} {...p} />,
    h3: (p) => <Heading level={3} {...p} />,
    h4: (p) => <Heading level={4} {...p} />,
    p: (p) => <p className="type-lead my-4 max-w-[72ch]" {...p} />,
    ul: (p) => <ul className="type-lead my-4 max-w-[72ch] list-disc space-y-1.5 pl-6 marker:text-subtle-foreground" {...p} />,
    ol: (p) => <ol className="type-lead my-4 max-w-[72ch] list-decimal space-y-2 pl-6 marker:font-semibold" {...p} />,
    li: (p) => <li className="pl-1" {...p} />,
    strong: (p) => <strong className="font-semibold" {...p} />,
    hr: () => <hr className="my-10 border-border" />,
    blockquote: (p) => (
      <blockquote className="my-6 max-w-[72ch] border-l-[3px] border-hn-slate bg-canvas px-4 py-1 text-muted-foreground dark:border-hn-cyan" {...p} />
    ),
    a: ({ href = "", children, ...rest }) => {
      const r = resolveHref(href, from, pages);
      if (r.kind === "page") {
        return (
          <Link href={r.href} className={linkClass}>
            {children}
          </Link>
        );
      }
      if (r.kind === "external") {
        return (
          <a href={r.href} target="_blank" rel="noreferrer noopener" className={cn(linkClass, "break-words")} {...rest}>
            {children}
            <span className="sr-only"> (otwiera się w nowej karcie)</span>
          </a>
        );
      }
      return (
        <a href={r.href} className={linkClass} {...rest}>
          {children}
        </a>
      );
    },
    code: (p) => <code className="type-code bg-muted px-1 py-0.5 break-words" {...p} />,
    pre: (p) => (
      <pre
        tabIndex={0}
        className="type-code my-6 overflow-x-auto bg-inverse p-4 text-inverse-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring [&_code]:bg-transparent [&_code]:p-0 [&_code]:break-normal"
        {...p}
      />
    ),
    table: (p) => (
      <div className="my-6 overflow-x-auto ring-1 ring-border">
        <table className="type-body w-full border-collapse" {...p} />
      </div>
    ),
    thead: (p) => <thead className="bg-muted [&:not(:has(th:not(:empty)))]:hidden" {...p} />,
    th: (p) => <th className="border-b border-border px-3 py-2 text-left align-bottom font-semibold" {...p} />,
    td: (p) => <td className="border-b border-border px-3 py-2 align-top [tr:last-child_&]:border-b-0" {...p} />,
    img: ({ alt = "", ...p }) => (
      // eslint-disable-next-line @next/next/no-img-element -- images in docs are plain files, not optimised assets
      <img alt={alt} className="my-6 h-auto max-w-full ring-1 ring-border" {...p} />
    ),
    // Parts of the pages that read live data; see components/docs/live.tsx.
    Note,
    DatasetFacts,
    DatasetMetadata,
    DictionaryDownloads,
    SchemaTable,
    SourcesTable,
  };
}

/** Compiles one page's MDX (trusted: it lives in this repository) and renders it with the site's styles. */
export async function DocBody({ source, meta, pages }: { source: string; meta: DocMeta; pages: DocMeta[] }) {
  const { default: Content } = await evaluate(source, {
    Fragment,
    jsx,
    jsxs,
    remarkPlugins: [remarkGfm],
    rehypePlugins: [rehypeSlug],
  });
  const byFile = new Map(pages.map((d) => [d.file, d.href]));
  return <Content components={elements(meta, byFile)} />;
}
