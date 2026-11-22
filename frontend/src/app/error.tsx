"use client";

import { ErrorScreen, ReloadButton } from "@/components/brand/error-screen";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorScreen
      code="500"
      title="Coś się wysypało"
      body="Serwer potknął się na tej stronie. Spróbuj jeszcze raz; jeśli to się powtarza, zajrzyj do logów."
      lines={[
        { kind: "cmd", text: "npm run hack" },
        { kind: "out", text: "Error: unexpected end of pizza" },
      ]}
      actions={<ReloadButton label="Spróbuj ponownie" onClick={reset} />}
      meta={
        error.digest ? (
          <span className="type-caption text-subtle-foreground">
            Kod błędu <span className="font-mono">{error.digest}</span>
          </span>
        ) : null
      }
    />
  );
}
