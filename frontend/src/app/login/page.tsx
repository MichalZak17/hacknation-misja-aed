import type { Metadata } from "next";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Logowanie" };

export default function LoginPage() {
  return (
    <main className="flex min-h-svh items-center justify-center bg-frame px-4 py-10">
      <LoginForm />
    </main>
  );
}
