import { existsSync } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";

import GithubSlugger from "github-slugger";
import matter from "gray-matter";

/**
 * The public documentation: every `*.mdx` file under the repository's `docs/` folder. The folder is read at build
 * time. It is `../docs` in the repository; the production image is built from frontend/ alone, so deploy.sh puts a
 * copy at `frontend/docs` and that one is used when there is no `../docs`. DOCS_DIR overrides both.
 */
const DOCS_DIR = path.resolve(
  process.env.DOCS_DIR ??
    [path.join(process.cwd(), "..", "docs"), path.join(process.cwd(), "docs")].find((dir) => existsSync(dir)) ??
    path.join(process.cwd(), "..", "docs"),
);

/** Files that are not pages on this site (a relative link to one goes to the repository instead). */
export const REPO_BLOB_URL = "https://github.com/MichalZak17/hacknation-misja-aed/blob/main";
export const REPO_TREE_URL = "https://github.com/MichalZak17/hacknation-misja-aed/tree/main";

/** Sidebar groups: the folder a page lives in, in the order they appear. Unknown folders follow, by name. */
const GROUPS: { dir: string; title: string }[] = [
  { dir: "", title: "Dane i publikacja" },
  { dir: "integrations", title: "Dodawanie źródeł" },
  { dir: "integrations/sources", title: "Opisy źródeł" },
  { dir: "llm-extraction", title: "Wzbogacanie danych" },
];

export type DocMeta = {
  /** Path segments under /docs; empty for the landing page. */
  slug: string[];
  href: string;
  /** Path of the .mdx file relative to docs/, with forward slashes. */
  file: string;
  title: string;
  /** Short label for the sidebar. */
  nav: string;
  description: string | null;
  group: string;
  order: number;
};

export type DocGroup = { title: string; docs: DocMeta[] };

export type TocItem = { id: string; text: string; level: 2 | 3 };

async function walk(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : Promise.resolve([path.join(dir, e.name)]))),
  );
  return nested.flat();
}

function plain(text: string) {
  return text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .trim();
}

function firstHeading(content: string) {
  return /^#\s+(.+)$/m.exec(content)?.[1];
}

/** Every documentation page, ordered the way the sidebar shows them. */
export async function listDocs(): Promise<DocMeta[]> {
  "use cache";
  // No docs folder (e.g. an image built from frontend/ alone) means an empty documentation, not a failed build.
  const files = (await walk(DOCS_DIR).catch(() => [])).filter((f) => f.endsWith(".mdx"));
  const docs = await Promise.all(
    files.map(async (abs): Promise<DocMeta> => {
      const file = path.relative(DOCS_DIR, abs).split(path.sep).join("/");
      const { data, content } = matter(await fs.readFile(abs, "utf8"));
      const segments = file.replace(/\.mdx$/, "").split("/");
      const slug = segments.at(-1) === "index" ? segments.slice(0, -1) : segments;
      const title = String(data.title ?? firstHeading(content) ?? segments.at(-1));
      return {
        slug,
        href: slug.length ? `/docs/${slug.join("/")}` : "/docs",
        file,
        title: plain(title),
        nav: plain(String(data.nav ?? title)),
        description: data.description ? String(data.description) : null,
        group: path.posix.dirname(file) === "." ? "" : path.posix.dirname(file),
        order: typeof data.order === "number" ? data.order : 100,
      };
    }),
  );
  return docs.sort((a, b) => groupRank(a.group) - groupRank(b.group) || a.order - b.order || a.nav.localeCompare(b.nav, "pl"));
}

function groupRank(dir: string) {
  const i = GROUPS.findIndex((g) => g.dir === dir);
  return i === -1 ? GROUPS.length : i;
}

export function groupDocs(docs: DocMeta[]): DocGroup[] {
  const groups: DocGroup[] = [];
  for (const doc of docs) {
    const title = GROUPS.find((g) => g.dir === doc.group)?.title ?? doc.group.split("/").at(-1) ?? "";
    const last = groups.at(-1);
    if (last && last.title === title) last.docs.push(doc);
    else groups.push({ title, docs: [doc] });
  }
  return groups;
}

export type Doc = { meta: DocMeta; source: string; toc: TocItem[] };

function tocOf(source: string): TocItem[] {
  const slugger = new GithubSlugger();
  const toc: TocItem[] = [];
  let fenced = false;
  for (const line of source.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
    if (fenced) continue;
    const m = /^(#{1,3})\s+(.+?)\s*#*\s*$/.exec(line);
    if (!m) continue;
    const text = plain(m[2]);
    const id = slugger.slug(text);
    if (m[1].length > 1) toc.push({ id, text, level: m[1].length as 2 | 3 });
  }
  return toc;
}

/** One page by its path segments, or null when there is no such file. */
export async function getDoc(slug: string[]): Promise<Doc | null> {
  "use cache";
  const meta = (await listDocs()).find((d) => d.slug.join("/") === slug.join("/"));
  if (!meta) return null;
  const { content } = matter(await fs.readFile(path.join(DOCS_DIR, meta.file), "utf8"));
  return { meta, source: content, toc: tocOf(content) };
}
