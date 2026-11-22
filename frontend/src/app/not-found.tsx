import Link from "next/link";

import { BackButton, ErrorScreen } from "@/components/brand/error-screen";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <ErrorScreen
      code="404"
      title="Tej strony tu nie ma"
      body="Adres prowadzi donikąd. Sprawdź link albo wróć na start."
      lines={[
        { kind: "cmd", text: "cd ./ta-strona" },
        { kind: "out", text: "cd: no such file or directory" },
      ]}
      actions={
        <>
          <Button asChild size="lg" variant="cta" framed>
            <Link href="/">Strona główna</Link>
          </Button>
          <BackButton label="Wróć" />
        </>
      }
    />
  );
}
