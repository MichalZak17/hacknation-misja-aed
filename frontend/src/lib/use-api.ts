"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

type State<T> = { data: T | undefined; error: ApiError | undefined; key: string | null };

/**
 * Fetches with `load` whenever `key` changes (null = don't fetch). `interval` (ms) re-fetches while set, e.g. while a
 * sync is running. Keeps the previous data while a new key loads, so tables don't flash empty.
 */
export function useApi<T>(key: string | null, load: () => Promise<T>, { interval }: { interval?: number } = {}) {
  const [state, setState] = useState<State<T>>({ data: undefined, error: undefined, key: null });
  const loadRef = useRef(load);
  const seq = useRef(0);

  useEffect(() => {
    loadRef.current = load;
  });

  const run = useCallback(async (forKey: string) => {
    const id = ++seq.current;
    try {
      const data = await loadRef.current();
      if (id === seq.current) setState({ data, error: undefined, key: forKey });
    } catch (e) {
      if (id === seq.current) {
        const error = e instanceof ApiError ? e : new ApiError(0, String(e));
        setState((s) => ({ data: s.data, error, key: forKey }));
      }
    }
  }, []);

  useEffect(() => {
    if (key === null) return;
    let cancelled = false;
    void (async () => {
      await Promise.resolve();
      if (!cancelled) await run(key);
    })();
    return () => {
      cancelled = true;
    };
  }, [key, run]);

  useEffect(() => {
    if (key === null || !interval) return;
    const timer = window.setInterval(() => void run(key), interval);
    return () => window.clearInterval(timer);
  }, [key, interval, run]);

  const reload = useCallback(() => (key === null ? Promise.resolve() : run(key)), [key, run]);

  return {
    data: state.data,
    error: state.error,
    loading: key !== null && state.key !== key,
    reload,
  };
}
