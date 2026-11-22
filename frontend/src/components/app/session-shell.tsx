"use client";

import { SignedIn, useOptionalSession } from "@/components/app/auth";
import { PublicShell } from "@/components/app/public-shell";
import { AppShell } from "@/components/app/shell";

/**
 * The frame for pages anyone may open (downloads, documentation): the panel's own shell for a signed-in admin, so
 * the navigation stays the same, and the public shell for everyone else. The page itself never requires a login.
 */
export function SessionShell({ children }: { children: React.ReactNode }) {
  const session = useOptionalSession();
  if (session) {
    return (
      <SignedIn email={session.email}>
        <AppShell>{children}</AppShell>
      </SignedIn>
    );
  }
  return <PublicShell>{children}</PublicShell>;
}
