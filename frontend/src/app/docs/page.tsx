import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { DocPage } from "@/app/docs/_components/doc-page";
import { getDoc } from "@/lib/docs";

export async function generateMetadata(): Promise<Metadata> {
  const doc = await getDoc([]);
  return doc ? { title: doc.meta.title, description: doc.meta.description ?? undefined } : {};
}

/** /docs: the landing page is docs/index.mdx. */
export default async function DocsIndex() {
  if (!(await getDoc([]))) notFound();
  return <DocPage slug={[]} />;
}
