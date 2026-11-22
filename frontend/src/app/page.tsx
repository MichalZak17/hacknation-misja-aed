import type { Metadata } from "next";

import { FindAed } from "@/app/_find/find-aed";
import { PublicFooter, PublicFrame } from "@/components/app/public-shell";

export const metadata: Metadata = {
  title: { absolute: "Znajdź najbliższy defibrylator AED · Misja AED" },
  description:
    "Mapa defibrylatorów AED w całej Polsce: najbliższe urządzenie, czy jest teraz dostępne, czy działa i jak do niego dojść. W nagłym wypadku dzwoń 112.",
};

/** The citizen's page, open to everyone: the nearest AED, whether it is open now and whether it works. The admin
 * dashboard lives at /panel. */
export default function FindAedPage() {
  return (
    <PublicFrame>
      <main id="main" className="flex-1">
        <FindAed />
      </main>
      <PublicFooter />
    </PublicFrame>
  );
}
