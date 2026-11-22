"use client";

import Link from "next/link";
import { useState } from "react";

import { HealthBadge, RunStrip } from "@/app/(app)/integrations/_components/health";
import { ErrorAlert, LoadingRows, PageHeader, Section } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type Integration, type Stats } from "@/lib/api";
import { formatDateTime, formatDuration, formatNumber, formatRelative } from "@/lib/format";
import { health, isActive, plural, pollInterval, runName, type Tone } from "@/lib/integrations";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

/**
 * The admin's first screen answers, in order: what needs me now, when did each source last sync and when is the
 * next one, what the registry holds, and whether the data answers the rescuer's question (where is the nearest AED,
 * can I get to it, does it work).
 */
export default function OverviewPage() {
  const stats = useApi("stats", api.stats, { interval: 60_000 });
  const [pollMs, setPollMs] = useState<number | undefined>(undefined);
  const sources = useApi("integrations", api.integrations, { interval: pollMs });
  const next = pollInterval(sources.data);
  if (next !== pollMs) setPollMs(next);
  const s = stats.data;

  return (
    <>
      <PageHeader title="Przegląd" description={s ? <Summary stats={s} sources={sources.data} /> : "Ładowanie stanu rejestru…"} />
      {stats.error ? <ErrorAlert error={stats.error} /> : null}

      <Section title="Do zrobienia">
        {!s || !sources.data ? <LoadingRows rows={3} /> : <Todo stats={s} sources={sources.data} />}
      </Section>

      <Section
        title="Synchronizacje"
        className="mt-6"
        actions={
          <Link href="/integrations" className="type-caption text-link hover:underline">
            Integracje
          </Link>
        }
      >
        {sources.error ? <ErrorAlert error={sources.error} /> : null}
        {sources.data ? <Syncs sources={sources.data} /> : <LoadingRows rows={6} />}
      </Section>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Urządzenia">{s ? <DeviceStats stats={s} /> : <LoadingRows rows={8} />}</Section>
        <Section title="Kompletność danych">{s ? <Completeness stats={s} /> : <LoadingRows rows={8} />}</Section>
      </div>
    </>
  );
}

function Summary({ stats: s, sources }: { stats: Stats; sources: Integration[] | undefined }) {
  const live = sources?.filter((i) => i.enabled).length;
  return (
    <>
      {formatNumber(s.active_devices)} {plural(s.active_devices, "defibrylator", "defibrylatory", "defibrylatorów")} w
      rejestrze
      {live !== undefined ? ` z ${live} ${plural(live, "źródła", "źródeł", "źródeł")}` : ""}. Stan z{" "}
      {formatDateTime(s.generated_at)}, wersja danych {s.data_version}.
    </>
  );
}

type Task = { key: string; tone: Tone; text: string; href: string; action: string };

/** Everything that waits for a person, most urgent first. Nothing here means nothing to do. */
function Todo({ stats: s, sources }: { stats: Stats; sources: Integration[] }) {
  const tasks: Task[] = [];
  for (const i of sources) {
    if (health(i).tone === "negative")
      tasks.push({
        key: `fail-${i.slug}`,
        tone: "negative",
        text: `Synchronizacja „${i.name}” nie powiodła się.`,
        href: `/integrations/${i.slug}`,
        action: "Zobacz historię",
      });
  }
  if (s.pending_matches > 0)
    tasks.push({
      key: "matches",
      tone: "caution",
      text: `${formatNumber(s.pending_matches)} ${plural(s.pending_matches, "możliwy duplikat czeka", "możliwe duplikaty czekają", "możliwych duplikatów czeka")} na decyzję.`,
      href: "/matches",
      action: "Przejrzyj",
    });
  for (const i of sources) {
    if (i.enabled && !i.historical_completed_at && !i.running)
      tasks.push({
        key: `import-${i.slug}`,
        tone: "caution",
        text: i.accepts_upload ? `„${i.name}”: wgraj plik i zaimportuj dane.` : `„${i.name}” nie ma jeszcze danych.`,
        href: `/integrations/${i.slug}`,
        action: i.accepts_upload ? "Wgraj plik" : "Importuj",
      });
    else if (i.invalid_records > 0)
      tasks.push({
        key: `invalid-${i.slug}`,
        tone: "neutral",
        text: `„${i.name}”: ${formatNumber(i.invalid_records)} ${plural(i.invalid_records, "rekord odrzucony", "rekordy odrzucone", "rekordów odrzuconych")} przy walidacji.`,
        href: `/integrations/${i.slug}?tab=records`,
        action: "Pokaż rekordy",
      });
  }

  if (tasks.length === 0)
    return <p className="type-body text-muted-foreground">Nic nie czeka na decyzję. Wszystkie źródła działają.</p>;

  return (
    <ul className="-my-2 divide-y divide-border">
      {tasks.map((t) => (
        <li key={t.key} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
          <span aria-hidden className={cn("size-2 shrink-0 rounded-full", TONE_DOT[t.tone])} />
          <span className="type-body min-w-0 flex-1">{t.text}</span>
          <Button asChild variant="outline" size="sm">
            <Link href={t.href}>{t.action}</Link>
          </Button>
        </li>
      ))}
    </ul>
  );
}

const TONE_DOT: Record<Tone, string> = {
  positive: "bg-positive",
  info: "bg-info",
  caution: "bg-caution",
  negative: "bg-destructive",
  neutral: "bg-subtle-foreground",
};

/** Per source: the last run (what, when, how long, what changed), the schedule and the next run. */
function Syncs({ sources }: { sources: Integration[] }) {
  if (sources.length === 0) return <p className="type-body text-muted-foreground">Nie ma jeszcze żadnych źródeł.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Źródło</TableHead>
          <TableHead>Ostatnie uruchomienie</TableHead>
          <TableHead className="text-right max-md:hidden">Trwało</TableHead>
          <TableHead className="max-lg:hidden">Zmiany</TableHead>
          <TableHead>Następne</TableHead>
          <TableHead className="max-xl:hidden">Ostatnie 12</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sources.map((i) => {
          const r = i.last_run;
          const h = health(i);
          return (
            <TableRow key={i.slug}>
              <TableCell className="max-w-72">
                <Link href={`/integrations/${i.slug}`} className="block truncate font-medium hover:underline">
                  {i.name}
                </Link>
                <div className="mt-0.5">
                  <HealthBadge tone={h.tone} label={h.label} />
                </div>
              </TableCell>
              <TableCell>
                {r ? (
                  <>
                    <span title={formatDateTime(r.created_at)}>{formatRelative(r.created_at)}</span>
                    <div className="type-caption text-muted-foreground">
                      {runName(r)}
                      {r.status === "failed" ? <span className="text-destructive">, błąd</span> : null}
                      {isActive(r) ? ", w toku" : null}
                    </div>
                  </>
                ) : (
                  <span className="text-subtle-foreground">jeszcze nie</span>
                )}
              </TableCell>
              <TableCell className="text-right tabular-nums max-md:hidden">
                {r?.duration_ms != null ? formatDuration(r.duration_ms) : "–"}
              </TableCell>
              <TableCell className="type-caption text-muted-foreground max-lg:hidden">{r ? changes(r) : "–"}</TableCell>
              <TableCell>
                {!i.enabled ? (
                  <span className="text-subtle-foreground">wyłączone</span>
                ) : i.periodic_enabled && i.next_run_at ? (
                  <>
                    <span title={formatDateTime(i.next_run_at)}>{formatRelative(i.next_run_at)}</span>
                    <div className="type-caption text-muted-foreground">co {i.sync_interval_hours} godz.</div>
                  </>
                ) : (
                  <span className="text-muted-foreground">tylko ręcznie</span>
                )}
              </TableCell>
              <TableCell className="max-xl:hidden">
                <RunStrip runs={i.recent_runs} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

function changes(r: NonNullable<Integration["last_run"]>) {
  if (isActive(r) || r.status === "failed") return "–";
  const parts = (
    [
      ["nowe", r.created],
      ["zmienione", r.updated],
      ["usunięte", r.removed],
      ["błędne", r.invalid],
    ] as const
  )
    .filter(([, n]) => n > 0)
    .map(([word, n]) => `${word} ${formatNumber(n)}`);
  return parts.length ? parts.join(", ") : "bez zmian";
}

type Row = { label: string; n: number };

/** What the registry holds: how the devices can be reached, where they hang, how fresh the checks are. */
function DeviceStats({ stats: s }: { stats: Stats }) {
  const total = s.active_devices;
  const p = s.by_placement;
  const v = s.verification_age;
  const sc = s.by_source_count;
  const groups: { title: string; rows: Row[]; note?: string }[] = [
    {
      title: "Dostęp",
      rows: [
        { label: "Publiczny", n: s.by_access.public },
        { label: "Z ograniczeniami (np. w godzinach pracy)", n: s.by_access.limited },
        { label: "Prywatny", n: s.by_access.private },
        { label: "Nieznany", n: s.by_access.unknown },
      ],
    },
  ];
  if (p)
    groups.push({
      title: "Gdzie się znajduje",
      rows: [
        { label: "W budynku", n: p.inside_building },
        { label: "Na zewnętrznej ścianie budynku", n: p.outside_on_building },
        { label: "Wolnostojący na zewnątrz", n: p.freestanding_outdoor },
        { label: "W pojeździe (straż, pogotowie)", n: p.vehicle },
        { label: "Nie wiadomo", n: p.unknown },
      ],
    });
  if (v)
    groups.push({
      title: "Ostatnie sprawdzenie na miejscu",
      rows: [
        { label: "W ostatnim roku", n: v.last_year },
        { label: "1–3 lata temu", n: v.one_to_three_years },
        { label: "Ponad 3 lata temu", n: v.older },
        { label: "Brak daty", n: v.never },
      ],
    });
  if (sc)
    groups.push({
      title: "Potwierdzone przez źródła",
      rows: [
        { label: "Jedno źródło", n: sc.one },
        { label: "Dwa źródła", n: sc.two },
        { label: "Trzy lub więcej", n: sc.three_or_more },
      ],
      note: "Urządzenie z kilku źródeł ma pola uzupełnione z każdego z nich, według priorytetu.",
    });
  return <Groups groups={groups} total={total} />;
}

/**
 * Coverage of what a person looking for an AED needs, grouped by their three questions. Open sources rarely publish
 * service data, so the last group is honest about how little is known.
 */
function Completeness({ stats: s }: { stats: Stats }) {
  const c = s.completeness;
  if (!c) return <p className="type-body text-muted-foreground">Liczby pojawią się po odświeżeniu statystyk (do 5 minut).</p>;
  const groups: { title: string; rows: Row[]; note?: string }[] = [
    {
      title: "Gdzie jest?",
      rows: [
        { label: "Adres", n: c.address },
        { label: "Opis miejsca (budynek, piętro, gdzie wisi)", n: c.location_detail },
        ...(c.photo !== undefined ? [{ label: "Zdjęcie", n: c.photo }] : []),
      ],
    },
    {
      title: "Czy można do niego dojść?",
      rows: [
        { label: "Znane zasady dostępu", n: c.access_known },
        { label: "Godziny dostępności", n: c.opening_hours },
      ],
    },
    {
      title: "Czy działa?",
      rows: [
        { label: "Daty serwisowe (elektrody, bateria, przegląd)", n: c.maintenance },
        { label: "Potwierdzona gotowość", n: s.by_readiness.ready },
        ...(c.operator !== undefined ? [{ label: "Znany dysponent", n: c.operator }] : []),
      ],
      note:
        s.by_readiness.attention || s.by_readiness.expired
          ? `Wymaga uwagi ${formatNumber(s.by_readiness.attention)}, po terminie ${formatNumber(s.by_readiness.expired)}.`
          : "Otwarte źródła nie publikują danych serwisowych. Podają je tylko dysponenci w swoich plikach.",
    },
  ];
  return <Groups groups={groups} total={s.active_devices} />;
}

function Groups({ groups, total }: { groups: { title: string; rows: Row[]; note?: string }[]; total: number }) {
  return (
    <div className="flex flex-col gap-5">
      {groups.map((g) => (
        <div key={g.title}>
          <h3 className="type-h4 mb-2">{g.title}</h3>
          <ul className="flex flex-col gap-2.5">
            {g.rows.map((r) => (
              <li key={r.label}>
                <Meter label={r.label} n={r.n} total={total} />
              </li>
            ))}
          </ul>
          {g.note ? <p className="type-caption mt-2 text-muted-foreground">{g.note}</p> : null}
        </div>
      ))}
    </div>
  );
}

function Meter({ label, n, total }: Row & { total: number }) {
  const share = total ? n / total : 0;
  const pct = share === 0 ? "0%" : share < 0.01 ? "<1%" : `${Math.round(share * 100)}%`;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="type-body">{label}</span>
        <span className="type-body shrink-0 tabular-nums">
          <span className="font-semibold">{formatNumber(n)}</span>
          <span className="type-caption text-muted-foreground"> {pct}</span>
        </span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={n}
        aria-valuetext={`${formatNumber(n)} z ${formatNumber(total)}, ${pct}`}
        className="mt-1 h-1.5 bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${Math.min(100, share * 100)}%` }} />
      </div>
    </div>
  );
}
