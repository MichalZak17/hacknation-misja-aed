import { notFound } from "next/navigation";

import { DocsNav } from "@/app/docs/_components/docs-nav";
import { SessionShell } from "@/components/app/session-shell";
import { groupDocs, listDocs } from "@/lib/docs";
import { DOCS_ENABLED } from "@/lib/features";

/** Hidden in production (lib/features.ts): every /docs URL is a 404 there. The documentation is the `*.mdx` files in the repository's docs/ folder. */
export default async function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (!DOCS_ENABLED) notFound();
  const groups = groupDocs(await listDocs());
  return (
    <SessionShell>
      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <DocsNav groups={groups} />
        {children}
      </div>
    </SessionShell>
  );
}
