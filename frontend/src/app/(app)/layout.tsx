import { AuthGate } from "@/components/app/auth";
import { AppShell } from "@/components/app/shell";

/** Everything except /login sits behind the session check. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <AppShell>{children}</AppShell>
    </AuthGate>
  );
}
