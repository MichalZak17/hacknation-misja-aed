import type { Metadata } from "next";

import { PageHeader } from "@/components/app/ui";

import { AedMap } from "./aed-map";

export const metadata: Metadata = { title: "Mapa" };

export default function MapPage() {
  return (
    <>
      <PageHeader title="Mapa" />
      <AedMap />
    </>
  );
}
