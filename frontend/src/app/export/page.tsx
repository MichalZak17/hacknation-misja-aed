import type { Metadata } from "next";

import { ExportView } from "./export-view";
import { SessionShell } from "@/components/app/session-shell";

export const metadata: Metadata = {
  title: "Dane do pobrania",
  description:
    "Ogólnopolski zbiór defibrylatorów AED w formatach CSV, GeoJSON i JSON, z metadanymi do publikacji na dane.gov.pl.",
};

/** Public: no login (admins see it in the panel's shell). Everything else sits behind the session check in (app)/layout.tsx. */
export default function ExportPage() {
  return (
    <SessionShell>
      <ExportView />
    </SessionShell>
  );
}
