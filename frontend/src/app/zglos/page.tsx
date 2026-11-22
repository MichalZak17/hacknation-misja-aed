import type { Metadata } from "next";
import { Suspense } from "react";

import { ReportForm } from "./report-form";
import { SessionShell } from "@/components/app/session-shell";
import { LoadingRows } from "@/components/app/ui";

export const metadata: Metadata = {
  title: "Zgłoś AED lub błąd",
  description:
    "Brakuje defibrylatora na mapie, jest w innym miejscu, nie działa albo jest zamknięty? Zgłoś to. Dysponenci AED mogą tu przekazać dane o swoim urządzeniu.",
};

/** Public: anyone can send a report, no login. Admins read them in the panel at /zgloszenia. */
export default function ReportPage() {
  return (
    <SessionShell>
      {/* The form reads ?aed= from the URL, so it renders in the browser */}
      <Suspense fallback={<LoadingRows rows={8} />}>
        <ReportForm />
      </Suspense>
    </SessionShell>
  );
}
