/**
 * What the integrations screens say about a source, derived in one place: its health, how to describe a run, and how
 * often to poll. Components render these; they don't re-derive them.
 */
import type { Integration, RunBrief, SyncRun } from "@/lib/api";
import { formatDuration, formatNumber, formatRelative } from "@/lib/format";

export type Tone = "positive" | "info" | "caution" | "negative" | "neutral";

export type Health = {
  tone: Tone;
  /** Two or three words for a badge or a list cell. */
  label: string;
  /** One sentence for the detail page: what is going on and what happens next. */
  sentence: string;
};

export function isActive(run: Pick<RunBrief, "status"> | null | undefined) {
  return run?.status === "queued" || run?.status === "running";
}

/** The latest run that wrote data (a check without saving says nothing about what is published). */
function lastRealRun(i: Integration) {
  return i.recent_runs.find((r) => !r.dry_run && !isActive(r)) ?? null;
}

export function health(i: Integration): Health {
  const next =
    i.enabled && i.periodic_enabled && i.next_run_at
      ? `Następna synchronizacja ${formatRelative(i.next_run_at)}.`
      : "Synchronizacja tylko ręcznie.";
  if (!i.enabled)
    return { tone: "neutral", label: "Wyłączone", sentence: "Dane zostają w zbiorze, ale nie są odświeżane." };
  if (i.running || isActive(i.last_run)) {
    const queued = i.last_run?.status === "queued";
    return {
      tone: "info",
      label: queued ? "W kolejce" : "Synchronizuje",
      sentence: queued ? "Synchronizacja czeka w kolejce." : "Trwa synchronizacja. Strona odświeża się sama.",
    };
  }
  if (!i.historical_completed_at)
    return {
      tone: "caution",
      label: "Bez importu",
      sentence: i.accepts_upload
        ? "Nie ma jeszcze danych. Wgraj plik dysponenta i zaimportuj go."
        : "Nie ma jeszcze danych. Zaimportuj cały zbiór, żeby urządzenia trafiły do rejestru.",
    };
  const real = lastRealRun(i);
  if (real?.status === "failed")
    return {
      tone: "negative",
      label: "Błąd",
      sentence: i.last_success_at
        ? `Synchronizacja ${formatRelative(real.created_at)} nie powiodła się. W zbiorze zostają dane odświeżone ${formatRelative(i.last_success_at)}.`
        : `Synchronizacja ${formatRelative(real.created_at)} nie powiodła się. Szczegóły są w historii.`,
    };
  if (i.invalid_records > 0)
    return {
      tone: "caution",
      label: "Działa, z uwagami",
      sentence: `${formatNumber(i.invalid_records)} ${plural(i.invalid_records, "rekord nie przeszedł", "rekordy nie przeszły", "rekordów nie przeszło")} walidacji i ${plural(i.invalid_records, "nie trafił", "nie trafiły", "nie trafiło")} do rejestru. ${next}`,
    };
  return { tone: "positive", label: "Działa", sentence: `Dane odświeżone ${formatRelative(i.last_success_at)}. ${next}` };
}

/** How the source delivers data, in the admin's words rather than the connector's class name. */
export function deliveryLabel(i: Integration) {
  const format = i.format ? i.format.toUpperCase() : null;
  if (i.accepts_upload) return "Plik wgrywany ręcznie (CSV lub XLSX)";
  return format ? `Pobierane z adresu, ${format}` : "Pobierane z adresu";
}

export function runName(r: Pick<RunBrief, "kind" | "dry_run">) {
  if (r.dry_run) return "Sprawdzenie bez zapisu";
  return r.kind === "historical" ? "Import całego zbioru" : "Synchronizacja";
}

export const TRIGGER_PHRASE: Record<string, string> = {
  manual: "uruchomione ręcznie",
  schedule: "z harmonogramu",
  seed: "przy pierwszym uruchomieniu",
};

/** The counts that say something: zeros are dropped, and a finished run with no changes reads "bez zmian". */
export function runSummary(r: SyncRun) {
  if (isActive(r)) return null;
  if (r.status === "failed") return r.duration_ms !== null ? `przerwane po ${formatDuration(r.duration_ms)}` : null;
  const parts = [`pobrano ${formatNumber(r.fetched)}`];
  const changed = (
    [
      ["nowe", r.created],
      ["zmienione", r.updated],
      ["usunięte", r.removed],
      ["błędne", r.invalid],
    ] as const
  ).filter(([, n]) => n > 0);
  if (changed.length === 0) parts.push("bez zmian");
  else parts.push(...changed.map(([word, n]) => `${word} ${formatNumber(n)}`));
  if (r.duration_ms !== null) parts.push(formatDuration(r.duration_ms));
  return parts.join(", ");
}

/** Poll quickly while anything is queued or running, otherwise slowly. */
export function pollInterval(integrations: Integration[] | undefined) {
  if (!integrations) return undefined;
  return integrations.some((i) => i.running || isActive(i.last_run)) ? 3000 : 30000;
}

/** Polish plural: 1 rekord, 2–4 rekordy, 5+ rekordów (12–14 take the last form). */
export function plural(n: number, one: string, few: string, many: string) {
  if (n === 1) return one;
  const tens = n % 100;
  const units = n % 10;
  return units >= 2 && units <= 4 && (tens < 12 || tens > 14) ? few : many;
}

/** Validation issue codes from the sync engine (backend/integrations/engine.py), in the admin's words. */
const ISSUE_TEXT: Record<string, string> = {
  missing_id: "brak identyfikatora w źródle",
  duplicate_id: "identyfikator powtarza się w źródle",
  missing_coordinates: "brak współrzędnych",
  coordinates_swapped: "zamienione szerokość i długość (poprawione)",
  outside_poland: "współrzędne poza Polską",
  outside_municipality: "współrzędne poza obszarem tego źródła",
};

export function issueText(code: string) {
  const [key, arg] = code.split(":", 2);
  if (key === "shared_coordinates") return `te same współrzędne co rekord ${arg}`;
  return ISSUE_TEXT[key] ?? code;
}
