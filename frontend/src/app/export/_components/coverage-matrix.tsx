"use client";

import { ErrorAlert, LoadingRows, Section } from "@/components/app/ui";
import { api, type CoverageCell, type SourceCoverage } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const LEVEL_HINTS: Record<number, string> = {
  1: "wymagany",
  2: "dostępność i lokalizacja w obiekcie",
  3: "dane serwisowe dysponenta",
};

/** Four steps, not a gradient: the number in the cell carries the value, the tint only helps scanning. */
const STEPS = [
  { label: "0%", mix: 0 },
  { label: "do 25%", mix: 10 },
  { label: "25–75%", mix: 20 },
  { label: "ponad 75%", mix: 32 },
] as const;

function step(pct: number) {
  if (pct <= 0) return STEPS[0];
  if (pct < 25) return STEPS[1];
  if (pct < 75) return STEPS[2];
  return STEPS[3];
}

function tint(mix: number): React.CSSProperties | undefined {
  // --info is dark teal in light mode and cyan in dark mode; at ≤32% the cell keeps ≥ 6:1 with --foreground in both
  return mix ? { backgroundColor: `color-mix(in oklab, var(--info) ${mix}%, transparent)` } : undefined;
}

const pctFmt = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 1 });

function formatPct(pct: number) {
  if (pct === 0) return "0%";
  if (pct < 0.1) return "<0,1%";
  if (pct >= 10 && pct < 99.5) return `${Math.round(pct)}%`;
  return `${pctFmt.format(pct)}%`;
}

/** "Warszawa 19115 / Otwarte dane Warszawy" → "Warszawa 19115"; the full name stays in the title. */
function shortName(name: string) {
  return name.split(/ — | \/ /)[0];
}

const METHOD_LABELS: Record<string, string> = { inferred: "z opisu", geocoded: "z granic PRG" };

export function CoverageMatrix() {
  const coverage = useApi("source-coverage", api.sourceCoverage);
  const c = coverage.data;

  return (
    <Section title="Zakres danych według źródeł">
      <p className="type-body mb-4 max-w-3xl text-muted-foreground">
        Które pola wzorcowego zakresu danych podaje każde źródło: odsetek jego rekordów z wypełnionym polem. Ostatnia
        kolumna to zbiór scalony, po połączeniu źródeł i uzupełnieniu braków.
      </p>
      {coverage.error ? <ErrorAlert error={coverage.error} /> : null}
      {c ? <Matrix coverage={c} /> : coverage.error ? null : <LoadingRows rows={6} />}
    </Section>
  );
}

function Matrix({ coverage: c }: { coverage: SourceCoverage }) {
  const columns = c.sources.length + 2;
  return (
    <>
      <Legend />
      <div
        role="region"
        aria-label="Zakres danych według źródeł, tabela przewijana w poziomie"
        tabIndex={0}
        className="relative mt-3 overflow-x-auto ring-1 ring-border outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <table className="w-full border-collapse text-sm">
          <caption className="type-caption caption-bottom border-t border-border px-3 py-2 text-left text-muted-foreground">
            Odsetek rekordów źródła, w których pole jest wypełnione (liczbę rekordów pokazuje podpowiedź). „Z opisu”:
            odczytane z opisu tekstowego źródła, „z granic PRG”: ustalone ze współrzędnych i granic gmin. Stan na{" "}
            {formatDateTime(c.generated_at)}.
          </caption>
          <thead>
            <tr className="border-b border-border">
              <th
                scope="col"
                className="type-label sticky left-0 z-10 min-w-36 bg-card px-3 py-2 text-left align-bottom text-subtle-foreground sm:min-w-52"
              >
                Pole
              </th>
              {c.sources.map((s) => (
                <th
                  key={s.slug}
                  scope="col"
                  title={`${s.name} (${s.publisher})`}
                  className="min-w-24 px-2 py-2 text-right align-bottom font-semibold text-foreground"
                >
                  <span className="block leading-tight">{shortName(s.name)}</span>
                  <span className="type-micro block font-normal text-muted-foreground tabular-nums">
                    {formatNumber(s.records)} rek.
                  </span>
                </th>
              ))}
              <th
                scope="col"
                className="min-w-28 border-l-2 border-border px-2 py-2 text-right align-bottom font-semibold text-hn-heading"
              >
                <span className="block leading-tight">Zbiór scalony</span>
                <span className="type-micro block font-normal text-muted-foreground tabular-nums">
                  {formatNumber(c.merged.records)} urz.
                </span>
              </th>
            </tr>
          </thead>
          {c.levels.map((level) => (
            <tbody key={level.level}>
              <tr className="border-b border-border bg-muted">
                <th scope="rowgroup" colSpan={columns} className="px-0 py-1.5 text-left">
                  <span className="type-label sticky left-0 inline-block px-3 text-foreground">
                    Poziom {level.level} · {level.label}
                    <span className="font-normal text-muted-foreground"> — {LEVEL_HINTS[level.level]}</span>
                  </span>
                </th>
              </tr>
              {c.fields
                .filter((f) => f.level === level.level)
                .map((f) => (
                  <tr key={f.field} className="border-b border-border last:border-0">
                    <th scope="row" className="sticky left-0 z-10 bg-card px-3 py-1.5 text-left align-top font-normal">
                      <span className="block leading-snug text-foreground">{f.label}</span>
                      <code className="type-micro hidden text-muted-foreground sm:block">{f.field}</code>
                    </th>
                    {c.sources.map((s) => (
                      <SourceCell key={s.slug} cell={f.sources[s.slug] ?? null} total={s.records} />
                    ))}
                    <MergedCell cell={f.merged} total={c.merged.records} />
                  </tr>
                ))}
            </tbody>
          ))}
        </table>
      </div>
    </>
  );
}

function Legend() {
  return (
    <div className="type-caption flex flex-wrap items-center gap-x-4 gap-y-1 text-muted-foreground">
      <span>Skala:</span>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {STEPS.map((s) => (
          <li key={s.label} className="flex items-center gap-1.5">
            <span aria-hidden className="inline-block size-3.5 ring-1 ring-border" style={tint(s.mix)} />
            {s.label}
          </li>
        ))}
      </ul>
      <span className="sm:hidden">Tabelę przewiniesz w bok.</span>
    </div>
  );
}

function SourceCell({ cell, total }: { cell: CoverageCell | null; total: number }) {
  if (cell === null || cell.pct === null) {
    const note = cell === null ? "nadawane przy scalaniu" : "brak rekordów";
    return (
      <td title={note} className="px-2 py-1.5 text-right align-top text-muted-foreground">
        <span aria-hidden>–</span>
        <span className="sr-only">{note}</span>
      </td>
    );
  }
  const counts = `${formatNumber(cell.count)} z ${formatNumber(total)} rekordów`;
  return (
    <td
      title={counts}
      style={tint(step(cell.pct).mix)}
      className={cn(
        "px-2 py-1.5 text-right align-top tabular-nums",
        cell.count ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {formatPct(cell.pct)}
      <span className="sr-only"> ({counts})</span>
    </td>
  );
}

function MergedCell({ cell, total }: { cell: SourceCoverage["fields"][number]["merged"]; total: number }) {
  const pct = cell.pct ?? 0;
  const derived = Object.entries(METHOD_LABELS)
    .map(([method, label]) => {
      const n = cell.by_source.filter((b) => b.method === method).reduce((sum, b) => sum + b.count, 0);
      return { label, n };
    })
    .filter((d) => d.n > 0);
  const breakdown = cell.by_source
    .map((b) => `${b.source}${b.method in METHOD_LABELS ? ` (${METHOD_LABELS[b.method]})` : ""}: ${formatNumber(b.count)}`)
    .join("\n");
  const counts = `${formatNumber(cell.count)} z ${formatNumber(total)} urządzeń`;
  return (
    <td
      title={breakdown ? `${counts}\n${breakdown}` : counts}
      style={tint(step(pct).mix)}
      className={cn(
        "border-l-2 border-border px-2 py-1.5 text-right align-top font-semibold tabular-nums",
        cell.count ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {formatPct(pct)}
      <span className="sr-only"> ({counts})</span>
      {derived.map((d) => (
        <span key={d.label} className="type-micro block font-normal whitespace-nowrap text-foreground">
          {d.label}: {formatPct((100 * d.n) / total)}
        </span>
      ))}
    </td>
  );
}
