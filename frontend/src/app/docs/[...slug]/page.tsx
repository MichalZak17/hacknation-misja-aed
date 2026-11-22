import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { DocPage } from "@/app/docs/_components/doc-page";
import { getDoc, listDocs } from "@/lib/docs";

export async function generateStaticParams() {
  return (await listDocs()).filter((d) => d.slug.length > 0).map((d) => ({ slug: d.slug }));
}

export async function generateMetadata({ params }: PageProps<"/docs/[...slug]">): Promise<Metadata> {
  const doc = await getDoc((await params).slug);
  return doc ? { title: doc.meta.title, description: doc.meta.description ?? undefined } : {};
}

/** /docs/<path>: the file docs/<path>.mdx. */
export default async function DocsPage({ params }: PageProps<"/docs/[...slug]">) {
  const { slug } = await params;
  if (!(await getDoc(slug))) notFound();
  return <DocPage slug={slug} />;
}
