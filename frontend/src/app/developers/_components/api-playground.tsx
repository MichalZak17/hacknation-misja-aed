"use client";

import { useEffect, useId, useMemo, useState, useSyncExternalStore } from "react";
import { CheckIcon, CopyIcon, LocateFixedIcon, PlayIcon, RotateCcwIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { copyText } from "@/lib/clipboard";
import { cn } from "@/lib/utils";

/**
 * An API reference block for one endpoint, used from MDX: the query parameters as a form, the request ready to copy
 * (cURL for Postman's Import → Raw text, JavaScript, Python), a "send" button that calls the API from the browser, and
 * an example response fetched live (so it never drifts from what the API returns).
 */

export type ApiParam = {
  name: string;
  type: "number" | "string" | "boolean" | "enum";
  required?: boolean;
  description: string;
  /** Pre-filled in the form. */
  default?: string;
  /** For `enum`: the allowed values. */
  values?: string[];
  placeholder?: string;
  /** "path" fills `{name}` in the endpoint path instead of the query string. */
  in?: "path" | "query";
};

type Lang = "curl" | "javascript" | "python";
const LANGS: { value: Lang; label: string }[] = [
  { value: "curl", label: "cURL" },
  { value: "javascript", label: "JavaScript" },
  { value: "python", label: "Python" },
];

/** Where the docs are not served from the API's own origin (e.g. while building), the public deployment. */
const PUBLIC_ORIGIN = "https://misja-aed.hackstorm.eu";

const noSubscribe = () => () => {};

type Result = { status: number; ms: number; body: string; ok: boolean };

function queryString(values: Record<string, string>, skip: Set<string> = new Set()) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(values)) if (!skip.has(k) && v.trim() !== "") qs.set(k, v.trim());
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** The path with `{name}` placeholders filled, and the query string of the other values. */
function requestPath(path: string, values: Record<string, string>, pathParams: Set<string>) {
  let filled = path;
  for (const name of pathParams) filled = filled.replace(`{${name}}`, encodeURIComponent(values[name]?.trim() ?? ""));
  return `${filled}${queryString(values, pathParams)}`;
}

function snippet(lang: Lang, method: string, url: string) {
  switch (lang) {
    case "curl":
      return `curl --request ${method} \\\n  --url '${url}' \\\n  --header 'Accept: application/json'`;
    case "javascript":
      return `const response = await fetch("${url}", {\n  method: "${method}",\n  headers: { Accept: "application/json" },\n});\nconst data = await response.json();\nconsole.log(data);`;
    case "python":
      return `import requests\n\nresponse = requests.${method.toLowerCase()}(\n    "${url}",\n    headers={"Accept": "application/json"},\n)\nprint(response.json())`;
  }
}

async function call(method: string, path: string): Promise<Result> {
  const started = performance.now();
  try {
    const res = await fetch(path, { method, headers: { Accept: "application/json" } });
    const text = await res.text();
    let body = text;
    try {
      body = JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      // not JSON: show as is
    }
    return { status: res.status, ms: Math.round(performance.now() - started), body, ok: res.ok };
  } catch (e) {
    return { status: 0, ms: Math.round(performance.now() - started), body: String(e), ok: false };
  }
}

export function ApiPlayground({
  method = "GET",
  path,
  params,
  example,
  exampleLabel = "Przykładowa odpowiedź",
}: {
  method?: "GET";
  path: string;
  params: ApiParam[];
  /** Extra query values for the example response (e.g. `{ demo: "true" }`), merged over the defaults. */
  example?: Record<string, string>;
  exampleLabel?: string;
}) {
  const initial = useMemo(() => Object.fromEntries(params.map((p) => [p.name, p.default ?? ""])), [params]);
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [lang, setLang] = useState<Lang>("curl");
  // The origin the page is served from (the API sits behind it); the public deployment while rendering on the server.
  const origin = useSyncExternalStore(
    noSubscribe,
    () => window.location.origin,
    () => PUBLIC_ORIGIN,
  );
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [sample, setSample] = useState<Result | null>(null);
  const [locating, setLocating] = useState<string | null>(null);
  const uid = useId();

  const pathParams = useMemo(() => new Set(params.filter((p) => p.in === "path").map((p) => p.name)), [params]);
  const examplePath = requestPath(path, { ...initial, ...example }, pathParams);
  useEffect(() => {
    let cancelled = false;
    void call(method, examplePath).then((r) => {
      if (!cancelled) setSample(r);
    });
    return () => {
      cancelled = true;
    };
  }, [method, examplePath]);

  const target = requestPath(path, values, pathParams);
  const url = `${origin}${target}`;
  const code = snippet(lang, method, url);
  const missing = params.filter((p) => p.required && !values[p.name]?.trim()).map((p) => p.name);
  const hasLocation = params.some((p) => p.name === "lat") && params.some((p) => p.name === "lon");

  const set = (name: string, value: string) => setValues((v) => ({ ...v, [name]: value }));

  async function send() {
    setSending(true);
    setResult(await call(method, target));
    setSending(false);
  }

  function locate() {
    if (!navigator.geolocation) {
      setLocating("Przeglądarka nie udostępnia położenia.");
      return;
    }
    setLocating("Ustalam położenie…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setValues((v) => ({ ...v, lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5) }));
        setLocating(null);
      },
      () => setLocating("Nie udało się ustalić położenia (brak zgody albo brak sygnału)."),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  const shown = result ?? sample;

  return (
    <section aria-label={`${method} ${path}`} className="not-prose my-8 grid gap-6 xl:grid-cols-2 xl:items-start">
      {/* Left: the endpoint and its parameters */}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 bg-canvas px-3 py-2 ring-1 ring-border">
          <Badge variant="positive" className="font-mono">
            {method}
          </Badge>
          <code className="type-code break-all">{path}</code>
        </div>

        <h3 className="type-label mt-6 mb-2 text-subtle-foreground">Parametry</h3>
        <ul className="divide-y divide-border ring-1 ring-border">
          {params.map((p) => {
            const id = `${uid}-${p.name}`;
            const describedBy = `${id}-desc`;
            return (
              <li key={p.name} className="grid gap-2 bg-background p-3 sm:grid-cols-[minmax(0,1fr)_11rem] sm:items-start">
                <div className="min-w-0">
                  <label htmlFor={id} className="flex flex-wrap items-baseline gap-x-2">
                    <code className="type-code font-semibold">{p.name}</code>
                    <span className="type-caption text-subtle-foreground">
                      {p.type === "enum" ? "string" : p.type}
                      {p.in === "path" ? " · w ścieżce" : ""}
                    </span>
                    {p.required ? (
                      <span className="type-caption font-semibold text-crimson-text">wymagany</span>
                    ) : (
                      <span className="type-caption text-subtle-foreground">opcjonalny</span>
                    )}
                  </label>
                  <p id={describedBy} className="type-caption mt-1 text-muted-foreground">
                    {p.description}
                    {p.values ? (
                      <>
                        {" "}
                        Wartości: {p.values.map((v, i) => (
                          <span key={v}>
                            {i ? ", " : ""}
                            <code className="type-code">{v}</code>
                          </span>
                        ))}
                        .
                      </>
                    ) : null}
                  </p>
                </div>
                {p.type === "boolean" || p.type === "enum" ? (
                  <NativeSelect
                    id={id}
                    aria-describedby={describedBy}
                    value={values[p.name]}
                    onChange={(e) => set(p.name, e.target.value)}
                    className="w-full"
                  >
                    <NativeSelectOption value="">—</NativeSelectOption>
                    {(p.type === "boolean" ? ["true", "false"] : (p.values ?? [])).map((v) => (
                      <NativeSelectOption key={v} value={v}>
                        {v}
                      </NativeSelectOption>
                    ))}
                  </NativeSelect>
                ) : (
                  <Input
                    id={id}
                    aria-describedby={describedBy}
                    aria-invalid={p.required && !values[p.name]?.trim() ? true : undefined}
                    inputMode={p.type === "number" ? "decimal" : undefined}
                    placeholder={p.placeholder}
                    value={values[p.name]}
                    onChange={(e) => set(p.name, e.target.value)}
                  />
                )}
              </li>
            );
          })}
        </ul>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {hasLocation ? (
            <Button type="button" variant="outline" size="sm" onClick={locate}>
              <LocateFixedIcon data-icon="inline-start" aria-hidden />
              Użyj mojej lokalizacji
            </Button>
          ) : null}
          <Button type="button" variant="ghost" size="sm" onClick={() => setValues(initial)}>
            <RotateCcwIcon data-icon="inline-start" aria-hidden />
            Przywróć przykład
          </Button>
          <span role="status" className="type-caption text-muted-foreground">
            {locating}
          </span>
        </div>
      </div>

      {/* Right: the request to copy, and the response */}
      <div className="flex min-w-0 flex-col gap-4 xl:sticky xl:top-20">
        <div className="bg-hn-terminal text-hn-terminal-foreground ring-1 ring-border">
          <div className="flex items-center gap-1 border-b border-white/10 px-2 py-1.5">
            <div role="tablist" aria-label="Język przykładu" className="flex gap-1">
              {LANGS.map((l) => (
                <button
                  key={l.value}
                  type="button"
                  role="tab"
                  aria-selected={lang === l.value}
                  onClick={() => setLang(l.value)}
                  className={cn(
                    "type-caption px-2 py-1 font-medium outline-none focus-visible:outline-2 focus-visible:outline-ring",
                    lang === l.value ? "bg-white/15 text-white" : "text-white/70 hover:text-white",
                  )}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <CopyButton value={code} label="Kopiuj żądanie" className="ms-auto" />
          </div>
          <pre
            tabIndex={0}
            className="type-code p-3 break-all whitespace-pre-wrap outline-none focus-visible:outline-2 focus-visible:outline-ring"
          >
            {code}
          </pre>
          <div className="flex flex-wrap items-center gap-2 border-t border-white/10 px-3 py-2">
            <span className="type-caption text-white/70">
              {missing.length ? `Uzupełnij: ${missing.join(", ")}` : "Wyśle prawdziwe zapytanie do API"}
            </span>
            <Button type="button" variant="cta" size="sm" className="ms-auto" disabled={sending || missing.length > 0} onClick={send}>
              {sending ? <Spinner data-icon="inline-start" /> : <PlayIcon data-icon="inline-start" aria-hidden />}
              Wyślij
            </Button>
          </div>
        </div>

        <div className="bg-hn-terminal text-hn-terminal-foreground ring-1 ring-border" aria-live="polite">
          <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-1.5">
            <span className="type-caption font-medium text-white">{result ? "Odpowiedź" : exampleLabel}</span>
            {shown ? (
              <span className={cn("type-caption font-mono", shown.ok ? "text-emerald-300" : "text-rose-300")}>
                {shown.status || "błąd sieci"} · {shown.ms} ms
              </span>
            ) : null}
            {result ? (
              <button
                type="button"
                onClick={() => setResult(null)}
                className="type-caption text-white/70 underline-offset-2 outline-none hover:text-white hover:underline focus-visible:outline-2 focus-visible:outline-ring"
              >
                pokaż przykład
              </button>
            ) : null}
            {shown ? <CopyButton value={shown.body} label="Kopiuj odpowiedź" className="ms-auto" /> : null}
          </div>
          <pre
            tabIndex={0}
            className="type-code max-h-[32rem] overflow-auto p-3 outline-none focus-visible:outline-2 focus-visible:outline-ring"
          >
            {shown ? shown.body : "Wczytuję przykład…"}
          </pre>
        </div>
      </div>
    </section>
  );
}

function CopyButton({ value, label, className }: { value: string; label: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(t);
  }, [copied]);
  return (
    <button
      type="button"
      onClick={async () => setCopied(await copyText(value))}
      className={cn(
        "type-caption inline-flex items-center gap-1.5 px-2 py-1 text-white/80 outline-none hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-ring",
        className,
      )}
    >
      {copied ? <CheckIcon aria-hidden className="size-3.5" /> : <CopyIcon aria-hidden className="size-3.5" />}
      {copied ? "Skopiowano" : label}
    </button>
  );
}
