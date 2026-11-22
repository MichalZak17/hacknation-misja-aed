"use client";

import { useState } from "react";

import { AccentBar, MetaLabel } from "@/components/brand";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError } from "@/lib/api";

/** Only same-site paths are followed after login. */
function nextPath() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/panel";
}

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(email.trim(), password);
      window.location.assign(nextPath());
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Nieprawidłowy e-mail lub hasło."
          : err instanceof ApiError
            ? err.detail
            : "Logowanie nie powiodło się.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-sm bg-card p-6 shadow-md ring-1 ring-border sm:p-8">
      <MetaLabel prompt tone="muted">
        HackNation 2026 · Ministerstwo Cyfryzacji
      </MetaLabel>
      <h1 className="type-h1 mt-2 text-hn-heading">Misja AED · dane</h1>
      <AccentBar className="mt-2 w-2/3" />
      <p className="type-body mt-4 text-muted-foreground">
        Panel integracji: źródła danych o defibrylatorach, synchronizacje i scalony zbiór.
      </p>
      <form onSubmit={submit} className="mt-6" noValidate suppressHydrationWarning>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="email">E-mail</FieldLabel>
            <Input suppressHydrationWarning
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="password">Hasło</FieldLabel>
            <Input suppressHydrationWarning
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error ? (
            <Alert variant="destructive" aria-live="assertive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <Button type="submit" variant="cta" size="lg" disabled={busy || !email || !password}>
            {busy ? <Spinner data-icon="inline-start" /> : null}
            Zaloguj się
          </Button>
        </FieldGroup>
      </form>
    </div>
  );
}
