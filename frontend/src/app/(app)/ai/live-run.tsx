"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangleIcon,
  CheckIcon,
  DatabaseIcon,
  DownloadCloudIcon,
  GitCompareIcon,
  ListChecksIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "lucide-react";

import { ErrorAlert, LoadingRows } from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { ApiError, api, type LiveEvent, type LivePhase, type RunLive } from "@/lib/api";
import { ENUM_LABELS, formatDuration, formatNumber, formatRelative } from "@/lib/format";
import { plural } from "@/lib/integrations";
import { animateSpring, prefersReducedMotion, SPRINGS } from "@/lib/spring";
import { cn } from "@/lib/utils";

const FEED_SIZE = 12;
const BACKLOG = 40; // answers waiting to be shown; older ones are skipped so the feed keeps up with the run

type FeedItem = LiveEvent & { fresh: boolean };

/** Polls one run about once a second and hands its new answers to a queue that the feed drains evenly. */
function useRunLive(runId: number) {
  const [data, setData] = useState<RunLive | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const pending = useRef<LiveEvent[]>([]);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let cursor = 0;
    let first = true;
    const tick = async () => {
      try {
        const next = await api.runLive(runId, cursor);
        if (cancelled) return;
        cursor = Math.max(cursor, ...next.events.map((e) => e.seq));
        const finished = next.run.finished_at !== null;
        if (first && (finished || next.events.length > 6)) {
          // Opening a finished run (or joining late): what happened so far appears at once, only new answers flow in
          const shown = finished ? next.events : next.events.slice(0, -4);
          const queued = finished ? [] : next.events.slice(-4);
          setFeed(shown.slice(-FEED_SIZE).reverse().map((e) => ({ ...e, fresh: false })));
          pending.current.push(...queued);
        } else {
          pending.current.push(...next.events);
        }
        first = false;
        if (pending.current.length > BACKLOG) pending.current.splice(0, pending.current.length - BACKLOG);
        setData(next);
        setError(null);
        if (!finished) timer = window.setTimeout(tick, 1000);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e : new ApiError(0, String(e)));
        timer = window.setTimeout(tick, 3000);
      }
    };
    void tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [runId]);

  useEffect(() => {
    let timer = 0;
    const drain = () => {
      const queue = pending.current;
      const item = queue.shift();
      if (item) setFeed((f) => [{ ...item, fresh: true }, ...f].slice(0, FEED_SIZE));
      // Spread a second's worth of answers over the next second; a long queue speeds up
      timer = window.setTimeout(drain, queue.length ? Math.max(80, Math.min(700, 1000 / queue.length)) : 200);
    };
    drain();
    return () => window.clearTimeout(timer);
  }, []);

  return { data, error, feed };
}

export function LiveRunView({
  runId,
  slug,
  concurrency,
  onFinished,
}: {
  runId: number;
  slug: string;
  concurrency: number;
  onFinished: () => void;
}) {
  const { data, error, feed } = useRunLive(runId);
  const finishedAt = data?.run.finished_at ?? null;
  const wasRunning = useRef(false);
  const onFinishedRef = useRef(onFinished);
  useEffect(() => {
    onFinishedRef.current = onFinished;
  });
  useEffect(() => {
    if (!data) return;
    if (!finishedAt) wasRunning.current = true;
    else if (wasRunning.current) {
      wasRunning.current = false;
      onFinishedRef.current();
    }
  }, [data, finishedAt]);

  if (error && !data) return <ErrorAlert error={error} />;
  if (!data) return <LoadingRows rows={6} />;

  const { live, run, summary } = data;
  const running = run.finished_at === null;
  const classifying = running && live.phase === "classify";

  return (
    <div data-motion="live" className="flex flex-col gap-6">
      <RunHeader data={data} />
      <PhaseStepper live={live} running={running} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-6">
          <Progress data={data} concurrency={concurrency} classifying={classifying} />
          <Feed feed={feed} running={running} slug={slug} hasClassify={Boolean(live.phases.classify) || live.total > 0} />
        </div>
        <Distribution live={live} />
      </div>
      {summary && !running ? <Summary data={data} /> : null}
    </div>
  );
}

const PHASES: { key: LivePhase; label: string; icon: typeof CheckIcon }[] = [
  { key: "fetch", label: "Pobieranie", icon: DownloadCloudIcon },
  { key: "validate", label: "Walidacja", icon: ShieldCheckIcon },
  { key: "diff", label: "Porównanie", icon: GitCompareIcon },
  { key: "classify", label: "Klasyfikacja AI", icon: SparklesIcon },
  { key: "write", label: "Zapis i scalanie", icon: DatabaseIcon },
  { key: "done", label: "Gotowe", icon: ListChecksIcon },
];

const PHASE_SENTENCE: Record<LivePhase, string> = {
  queued: "Synchronizacja czeka w kolejce.",
  fetch: "Pobieranie danych ze źródła.",
  validate: "Sprawdzanie współrzędnych i identyfikatorów.",
  diff: "Porównywanie z poprzednim stanem.",
  classify: "Model czyta opisy.",
  write: "Zapisywanie i scalanie w urządzenia.",
  done: "Zakończono.",
};

function RunHeader({ data }: { data: RunLive }) {
  const { run, live } = data;
  const running = run.finished_at === null;
  const pct = live.total ? Math.floor((live.done / live.total) * 10) * 10 : 0;
  // Screen readers hear phase changes and every tenth of the way, not every card
  const sentence = running
    ? `${PHASE_SENTENCE[live.phase] ?? ""}${live.phase === "classify" && live.total ? ` ${pct}% gotowe.` : ""}`
    : run.status === "success"
      ? "Klasyfikacja zakończona."
      : `Synchronizacja nie powiodła się: ${run.error}`;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="type-label text-subtle-foreground">Przebieg #{run.id}</span>
      {running ? (
        <Badge variant="info">
          <span aria-hidden className="ai-dot inline-block size-1.5 rounded-full bg-current" />
          Na żywo
        </Badge>
      ) : run.status === "success" ? (
        <Badge variant="positive">Zakończony</Badge>
      ) : (
        <Badge variant="destructive">Błąd</Badge>
      )}
      {run.reextract ? <Badge variant="outline">Ponowna klasyfikacja</Badge> : null}
      <span className="type-caption text-muted-foreground">
        {running ? `start ${formatRelative(run.started_at ?? run.created_at)}` : `zakończony ${formatRelative(run.finished_at)}`}
        {run.duration_ms ? ` · trwał ${formatDuration(run.duration_ms)}` : ""}
      </span>
      <p className="sr-only" aria-live="polite" role="status">
        {sentence}
      </p>
      {!running && run.status !== "success" && run.error ? (
        <p className="type-caption basis-full text-destructive">{run.error}</p>
      ) : null}
    </div>
  );
}

function PhaseStepper({ live, running }: { live: RunLive["live"]; running: boolean }) {
  const current = PHASES.findIndex((p) => p.key === live.phase);
  return (
    <ol className="grid grid-cols-2 gap-px bg-border ring-1 ring-border sm:grid-cols-3 lg:grid-cols-6" aria-label="Etapy synchronizacji">
      {PHASES.map((p, i) => {
        const skipped = p.key === "classify" && current > i && !live.phases.classify;
        const done = current > i || (p.key === "done" && live.phase === "done");
        const active = running && current === i;
        const state = active ? "w toku" : skipped ? "pominięty" : done ? "zakończony" : "oczekuje";
        const Icon = done && !skipped ? CheckIcon : p.icon;
        return (
          <li
            key={p.key}
            aria-current={active ? "step" : undefined}
            className={cn(
              "relative flex items-center gap-3 bg-card px-4 py-3",
              active && "bg-info-subtle",
              p.key === "classify" && active && "ai-glow",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "flex size-8 shrink-0 items-center justify-center ring-1",
                done && !skipped && "ai-check bg-positive text-positive-foreground ring-positive",
                active && "ai-pulse bg-info text-info-foreground ring-info",
                !done && !active && "text-subtle-foreground ring-border",
                skipped && "bg-muted text-subtle-foreground ring-border",
              )}
            >
              <Icon className="size-4" />
            </span>
            <span className="min-w-0">
              <span className="type-body block truncate font-medium">{p.label}</span>
              <span className="type-micro block text-subtle-foreground">{state}</span>
            </span>
            {active ? <span aria-hidden className="ai-progress-line absolute inset-x-0 bottom-0 h-0.5 bg-info" /> : null}
          </li>
        );
      })}
    </ol>
  );
}

/** A number that eases to its new value (instantly with reduced motion). */
function AnimatedNumber({ value, format = formatNumber }: { value: number; format?: (n: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const current = useRef(value);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion()) {
      current.current = value;
      el.textContent = format(value);
      return;
    }
    const spring = animateSpring([current.current], [value], [0], SPRINGS.snappy, ([v]) => {
      current.current = v;
      el.textContent = format(Math.round(v));
    });
    return () => spring.cancel();
  }, [value, format]);
  return <span ref={ref}>{format(value)}</span>;
}

function rateOf(points: [number, number][]) {
  if (points.length < 2) return 0;
  const last = points[points.length - 1];
  const from = points.find((p) => last[0] - p[0] <= 10) ?? points[0];
  return last[0] > from[0] ? (last[1] - from[1]) / (last[0] - from[0]) : 0;
}

function Progress({ data, concurrency, classifying }: { data: RunLive; concurrency: number; classifying: boolean }) {
  const { live, run } = data;
  const running = run.finished_at === null;
  const pct = live.total ? Math.min(100, (live.done / live.total) * 100) : 0;
  const rate = running ? rateOf(live.throughput) : live.elapsed ? (live.done - live.cache_hits) / live.elapsed : 0;
  const answered = live.done - live.cache_hits;
  const avgMs = answered > 0 ? live.ms_total / answered : 0;
  const remaining = live.total - live.done;
  const eta = running && rate > 0 && remaining > 0 ? remaining / rate : null;
  const inFlight = classifying ? Math.min(concurrency, Math.max(0, live.llm_calls - answered)) : 0;

  return (
    <section aria-label="Postęp klasyfikacji" className="bg-card p-4 ring-1 ring-border">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="type-h4">Postęp</h2>
        <span className="type-caption text-muted-foreground">
          {live.total
            ? `${formatNumber(live.total)} ${plural(live.total, "opis", "opisy", "opisów")} z ${formatNumber(live.records)} ${plural(live.records, "rekordu", "rekordów", "rekordów")} (identyczne teksty mają jedną odpowiedź)`
            : live.phase === "queued" || live.phase === "fetch"
              ? "Czekam na dane ze źródła…"
              : "W tym przebiegu nie było opisów do przeczytania."}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Przeczytane opisy"
        aria-valuemin={0}
        aria-valuemax={live.total || 1}
        aria-valuenow={live.done}
        className="relative mt-3 h-3 overflow-hidden bg-muted"
      >
        <div className={cn("ai-bar h-full bg-hn-crimson", classifying && "ai-stripes")} style={{ width: `${pct}%` }} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Przeczytane">
          <AnimatedNumber value={live.done} /> / {formatNumber(live.total)}
        </Stat>
        <Stat label="Zapytania do modelu">
          <AnimatedNumber value={answered} />
        </Stat>
        <Stat label="Z pamięci">
          <AnimatedNumber value={live.cache_hits} />
        </Stat>
        <Stat label="Tempo">{rate ? `${rate.toFixed(1)}/s` : "—"}</Stat>
        <Stat label="Średni czas odpowiedzi">{avgMs ? `${(avgMs / 1000).toFixed(1)} s` : "—"}</Stat>
        <Stat label={running ? "Pozostało" : "Błędy"}>
          {running ? (eta ? formatDuration(eta * 1000) : "—") : <AnimatedNumber value={live.failed} />}
        </Stat>
      </dl>
      <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
        <Sparkline points={live.throughput} />
        {concurrency > 0 ? (
          <div>
            <div className="type-micro mb-1 text-subtle-foreground">
              Równoległe zapytania: {inFlight} z {concurrency}
            </div>
            <div className="flex gap-1" aria-hidden>
              {Array.from({ length: concurrency }, (_, i) => (
                <span
                  key={i}
                  className={cn("h-6 w-2", i < inFlight ? "ai-worker bg-hn-cyan" : "bg-muted")}
                  style={{ ["--i" as string]: i }}
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
      {running && live.failed ? (
        <p className="type-caption mt-3 flex items-center gap-1.5 text-muted-foreground">
          <AlertTriangleIcon className="size-3.5 text-caution-icon" aria-hidden />
          {live.failed} {plural(live.failed, "zapytanie nie powiodło się", "zapytania nie powiodły się", "zapytań nie powiodło się")}; te rekordy zachowają poprzednią odpowiedź.
        </p>
      ) : null}
    </section>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="type-micro text-subtle-foreground">{label}</dt>
      <dd className="type-h4 tabular-nums">{children}</dd>
    </div>
  );
}

/** Answers per second over the run, from the cumulative (seconds, done) points. */
function Sparkline({ points }: { points: [number, number][] }) {
  if (points.length < 3) {
    return <div className="type-micro text-subtle-foreground">Wykres tempa pojawi się po kilku sekundach klasyfikacji.</div>;
  }
  const rates = points.slice(1).map((p, i) => {
    const dt = p[0] - points[i][0];
    return [p[0], dt > 0 ? (p[1] - points[i][1]) / dt : 0] as const;
  });
  const maxT = rates[rates.length - 1][0] || 1;
  const minT = rates[0][0];
  const maxR = Math.max(...rates.map((r) => r[1]), 1);
  const xy = rates.map(([t, r]) => `${(((t - minT) / (maxT - minT || 1)) * 300).toFixed(1)},${(40 - (r / maxR) * 36).toFixed(1)}`);
  return (
    <figure className="min-w-0">
      <figcaption className="type-micro mb-1 text-subtle-foreground">
        Odpowiedzi na sekundę (maks. {maxR.toFixed(1)})
      </figcaption>
      <svg viewBox="0 0 300 40" preserveAspectRatio="none" className="h-10 w-full" aria-hidden>
        <polygon points={`0,40 ${xy.join(" ")} 300,40`} className="fill-hn-crimson/10" />
        <polyline points={xy.join(" ")} fill="none" strokeWidth={1.5} vectorEffect="non-scaling-stroke" className="stroke-hn-crimson" />
      </svg>
    </figure>
  );
}

const INPUT_LABELS: Record<string, string> = {
  "defibrillator:location": "Lokalizacja",
  "defibrillator:location:pl": "Lokalizacja",
  "defibrillator:location:en": "Lokalizacja (EN)",
  description: "Opis",
  "description:pl": "Opis",
  note: "Notatka",
  fixme: "Do poprawy",
  location: "Położenie",
  opening_hours: "Godziny",
  level: "Piętro",
  indoor: "W budynku",
  access: "Dostęp",
};

const OUTPUT_ORDER = ["placement", "floor", "opening_hours", "access_conditions", "seasonal", "is_mobile", "indoor", "device_count", "enclosure", "position_hint"];
const OUTPUT_LABELS: Record<string, string> = {
  placement: "Umiejscowienie",
  floor: "Piętro",
  opening_hours: "Godziny",
  access_conditions: "Warunek dostępu",
  seasonal: "Sezonowy",
  is_mobile: "Mobilny",
  indoor: "W budynku",
  device_count: "Liczba AED",
  enclosure: "Obudowa",
  position_hint: "Wskazówka",
};
const ENCLOSURE_LABEL: Record<string, string> = { capsule: "kapsuła", cabinet: "szafka" };

function chipsOf(output: Record<string, unknown>): { field: string; label: string; value: string }[] {
  const chips: { field: string; label: string; value: string }[] = [];
  for (const field of OUTPUT_ORDER) {
    const value = output[field];
    if (value === undefined || value === null) continue;
    if (field === "access_conditions" && Array.isArray(value)) {
      for (const c of value) chips.push({ field, label: OUTPUT_LABELS[field], value: ENUM_LABELS.access_conditions[c] ?? String(c) });
      continue;
    }
    const text =
      field === "placement"
        ? ENUM_LABELS.placement[String(value)] ?? String(value)
        : field === "enclosure"
          ? ENCLOSURE_LABEL[String(value)] ?? String(value)
          : typeof value === "boolean"
            ? value
              ? "tak"
              : "nie"
            : String(value);
    chips.push({ field, label: OUTPUT_LABELS[field] ?? field, value: text });
  }
  return chips;
}

function Feed({ feed, running, slug, hasClassify }: { feed: FeedItem[]; running: boolean; slug: string; hasClassify: boolean }) {
  return (
    <section aria-label="Odpowiedzi modelu" className="bg-hn-terminal text-hn-terminal-foreground ring-1 ring-hn-terminal-line">
      <header className="flex items-center gap-3 border-b border-hn-terminal-line px-4 py-2">
        <span aria-hidden className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-hn-terminal-dot" />
          <span className="size-2.5 rounded-full bg-hn-terminal-dot" />
          <span className="size-2.5 rounded-full bg-hn-terminal-dot" />
        </span>
        <h2 className="type-code text-hn-terminal-muted">qwen ▸ {slug} ▸ odpowiedzi</h2>
        <span className="type-micro ml-auto hidden text-hn-terminal-muted md:inline">
          <span className="line-through">przekreślone</span> = źródło podaje to pole samo i ma pierwszeństwo
        </span>
        {running ? (
          <span className="type-micro flex items-center gap-1.5 text-hn-cyan">
            <span aria-hidden className="ai-dot inline-block size-1.5 rounded-full bg-hn-cyan" />
            na żywo
          </span>
        ) : null}
      </header>
      {feed.length === 0 ? (
        <p className="type-code px-4 py-8 text-hn-terminal-muted">
          {running
            ? "Czekam na pierwsze odpowiedzi modelu…"
            : hasClassify
              ? "Brak zapisanych odpowiedzi tego przebiegu."
              : "W tym przebiegu model nie miał nic do przeczytania: opisy się nie zmieniły. Użyj „Klasyfikuj ponownie”."}
          {running ? <span aria-hidden className="ai-caret ml-1 inline-block h-4 w-2 translate-y-0.5 bg-hn-cyan" /> : null}
        </p>
      ) : (
        <ol className="divide-y divide-hn-terminal-line">
          {feed.map((item) => (
            <FeedCard key={item.seq} item={item} />
          ))}
        </ol>
      )}
    </section>
  );
}

function FeedCard({ item }: { item: FeedItem }) {
  const chips = chipsOf(item.output);
  const inputs = Object.entries(item.input);
  return (
    <li className={cn("relative grid gap-4 overflow-hidden px-4 py-3 md:grid-cols-2", item.fresh && "ai-enter ai-scan")}>
      <div className="min-w-0">
        <div className="type-micro mb-1 flex flex-wrap items-center gap-2 text-hn-terminal-muted">
          <span className="font-mono">{item.source_record_id}</span>
          {item.records > 1 ? <span>· ten sam tekst w {item.records} rekordach</span> : null}
          {item.kind === "cache" ? <span className="text-hn-cyan">· z pamięci</span> : item.ms ? <span>· {(item.ms / 1000).toFixed(1)} s</span> : null}
        </div>
        <dl className="flex flex-col gap-1">
          {inputs.map(([k, v]) => (
            <div key={k} className="type-code flex gap-2">
              <dt className="shrink-0 text-hn-terminal-muted">{INPUT_LABELS[k] ?? k}:</dt>
              <dd className="min-w-0 break-words">{String(v)}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="min-w-0">
        <div className="type-micro mb-1 flex items-center gap-1.5 text-hn-cyan">
          <SparklesIcon className="size-3" aria-hidden />
          {item.kind === "failed" ? "Błąd modelu" : "Odczytane przez AI"}
        </div>
        {item.kind === "failed" ? (
          <p className="type-code text-hn-crimson">{item.error || "Brak odpowiedzi"}</p>
        ) : chips.length === 0 ? (
          <p className="type-code text-hn-terminal-muted">Nic konkretnego w tekście.</p>
        ) : (
          <ul className="flex flex-wrap gap-1.5">
            {chips.map((c, i) => {
              const sourceWins = item.source_wins.includes(c.field);
              return (
                <li
                  key={`${c.field}-${i}`}
                  className={cn(
                    "type-caption flex items-center gap-1.5 px-2 py-0.5 ring-1",
                    item.fresh && "ai-chip",
                    sourceWins
                      ? "text-hn-terminal-muted opacity-70 ring-hn-terminal-line"
                      : "bg-hn-cyan/10 text-hn-terminal-foreground ring-hn-cyan/40",
                  )}
                  style={{ ["--i" as string]: i }}
                  title={sourceWins ? "Źródło podaje to pole samo, więc jego wartość ma pierwszeństwo." : undefined}
                >
                  <span className="text-hn-terminal-muted">{c.label}</span>
                  <span className={cn(sourceWins && "line-through decoration-hn-terminal-muted")}>{c.value}</span>
                  {sourceWins ? <span className="sr-only">(źródło ma pierwszeństwo)</span> : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </li>
  );
}

function Bars({ title, counts, total, labels }: { title: string; counts: Record<string, number>; total: number; labels: Record<string, string> }) {
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <div>
      <h3 className="type-label mb-2 text-subtle-foreground">{title}</h3>
      {rows.length === 0 ? (
        <p className="type-caption text-subtle-foreground">Jeszcze nic.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map(([key, n]) => (
            <li key={key}>
              <div className="type-caption flex justify-between gap-2">
                <span className="truncate">{labels[key] ?? key}</span>
                <span className="tabular-nums text-muted-foreground">
                  <AnimatedNumber value={n} />
                  {total ? ` · ${Math.round((n / total) * 100)}%` : ""}
                </span>
              </div>
              <div className="mt-1 h-1.5 bg-muted">
                <div className="ai-bar h-full bg-hn-slate dark:bg-hn-cyan" style={{ width: `${(n / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Distribution({ live }: { live: RunLive["live"] }) {
  const t = live.tallies;
  const answered = Object.values(t.placement).reduce((a, b) => a + b, 0);
  return (
    <aside aria-label="Co model odczytał" className="flex flex-col gap-5 bg-card p-4 ring-1 ring-border">
      <h2 className="type-h4">Co model odczytał</h2>
      <dl className="grid grid-cols-3 gap-3">
        <Stat label="Godziny">
          <AnimatedNumber value={t.opening_hours} />
        </Stat>
        <Stat label="Piętro">
          <AnimatedNumber value={t.floor} />
        </Stat>
        <Stat label="Sezonowe">
          <AnimatedNumber value={t.seasonal} />
        </Stat>
      </dl>
      <Bars title="Umiejscowienie" counts={t.placement} total={answered} labels={ENUM_LABELS.placement} />
      <Bars title="Warunki dostępu" counts={t.access_conditions} total={answered} labels={ENUM_LABELS.access_conditions} />
    </aside>
  );
}

function Summary({ data }: { data: RunLive }) {
  const e = data.summary?.enrichment ?? {};
  const merge = data.summary?.merge ?? null;
  const ok = data.run.status === "success";
  if (!e.llm_calls && !e.cache_hits && !e.records) return null;
  return (
    <section aria-label="Podsumowanie" className="ai-enter border-l-4 border-positive-border bg-positive-subtle p-4 text-positive-subtle-foreground">
      <h2 className="type-h4">{ok ? "Klasyfikacja zakończona" : "Przebieg zakończony z błędem"}</h2>
      <p className="type-body mt-1">
        Model odpowiedział na {formatNumber((e.llm_calls ?? 0) - (e.failed ?? 0))} z {formatNumber(e.llm_calls ?? 0)} zapytań
        {e.cache_hits ? `, ${formatNumber(e.cache_hits)} odpowiedzi wzięto z pamięci` : ""}
        {e.seconds ? ` w ${formatDuration(e.seconds * 1000)}` : ""}. Zaktualizowano odczytane pola w {formatNumber(e.records_updated ?? 0)}{" "}
        {plural(e.records_updated ?? 0, "rekordzie", "rekordach", "rekordach")}
        {merge?.new_devices ? `; powstało ${formatNumber(merge.new_devices)} nowych urządzeń` : ""}. Urządzenia przeliczono z
        nowymi odpowiedziami.
      </p>
      {e.problem ? <p className="type-caption mt-1">Uwaga: {e.problem}</p> : null}
    </section>
  );
}
