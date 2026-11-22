"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { Spinner } from "@/components/ui/spinner";
import { api, ApiError } from "@/lib/api";

type Auth = { email: string; logout: () => Promise<void> };

const AuthContext = createContext<Auth | null>(null);

/**
 * The session as last seen in this tab: an email, null (no session) or undefined (not asked yet). Kept across
 * client-side navigation so a public page opened from the panel shows the panel's shell straight away.
 */
let lastSession: { email: string } | null | undefined;

async function logout() {
  try {
    await api.logout();
  } finally {
    window.location.replace("/login");
  }
}

/** Provides the signed-in account to the shell (the account menu) outside AuthGate. */
export function SignedIn({
  email,
  children,
}: {
  email: string;
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={{ email, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** For public pages: the session if there is one, never a redirect to /login. undefined while it's being checked. */
export function useOptionalSession() {
  const [session, setSession] = useState(lastSession);
  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => (lastSession = me))
      .catch(() => (lastSession = null))
      .then((s) => !cancelled && setSession(s));
    return () => {
      cancelled = true;
    };
  }, []);
  return session;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth outside AuthGate");
  return auth;
}

/** Client-side guard: asks /api/auth/me once; without a session it sends the person to /login?next=… */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<{ email: string } | "loading" | "offline">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => {
        lastSession = me;
        if (!cancelled) setState(me);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          lastSession = null;
          const next = window.location.pathname + window.location.search;
          window.location.replace(`/login?next=${encodeURIComponent(next)}`);
        } else {
          setState("offline");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ready = state !== "loading" && state !== "offline";
  return (
    <AuthContext.Provider value={{ email: ready ? state.email : "", logout }}>
      {state === "loading" ? (
        // <main>: while the app below is hidden, this is the page's only content and must sit in a landmark
        <main className="flex min-h-svh items-center justify-center text-muted-foreground">
          <div className="flex items-center gap-2" role="status">
            <Spinner /> <span className="type-body">Sprawdzanie sesji…</span>
          </div>
        </main>
      ) : null}
      {state === "offline" ? (
        <main
          className="mx-auto flex min-h-svh max-w-lg flex-col justify-center gap-3 px-4"
          aria-live="assertive"
        >
          <h1 className="type-h2 text-hn-heading">Brak połączenia z API</h1>
          <p className="type-body text-muted-foreground">
            Backend nie odpowiada. Uruchom go poleceniem{" "}
            <code className="type-code">npm run backend</code> i odśwież stronę.
          </p>
        </main>
      ) : null}
      {/*
        The app stays mounted (hidden) while the session is checked: the prerendered shell then contains the page, which
        Next's instant-navigation validation needs, and the page's own requests start right away. Those redirect to
        /login on 401 just like the check above.
      */}
      <div hidden={!ready} className={ready ? "contents" : undefined}>
        {children}
      </div>
    </AuthContext.Provider>
  );
}
