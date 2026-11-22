import type { Metadata } from "next";

import { DevelopersView } from "./developers-view";
import { SessionShell } from "@/components/app/session-shell";

export const metadata: Metadata = {
  title: "API dla deweloperów",
  description:
    "Publiczne API Misji AED: najbliższy defibrylator, czy jest dostępny teraz, AED w gminach i województwach, z gotowymi zapytaniami cURL do Postmana.",
};

/** Public: no login, like /export. */
export default function DevelopersPage() {
  return (
    <SessionShell>
      <DevelopersView />
    </SessionShell>
  );
}
