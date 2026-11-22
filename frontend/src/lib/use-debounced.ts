"use client";

import { useEffect, useState } from "react";

/** `value`, settled for `ms` — keeps search boxes from firing a request per keystroke. */
export function useDebounced<T>(value: T, ms = 300) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return settled;
}
