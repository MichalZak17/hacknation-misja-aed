/** Polish labels and formatting. `null` is shown as "brak danych", never guessed. */

export const NO_DATA = "brak danych";

const dateFmt = new Intl.DateTimeFormat("pl-PL", { day: "2-digit", month: "2-digit", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("pl-PL", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const numberFmt = new Intl.NumberFormat("pl-PL");
const relFmt = new Intl.RelativeTimeFormat("pl-PL", { numeric: "auto" });

export function formatNumber(n: number | null | undefined) {
  return n === null || n === undefined ? NO_DATA : numberFmt.format(n);
}

/** `YYYY-MM-DD` (a date, no timezone) or an ISO timestamp. */
export function formatDate(value: string | null | undefined) {
  if (!value) return NO_DATA;
  const d = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(d.getTime()) ? value : dateFmt.format(d);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return NO_DATA;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : dateTimeFmt.format(d);
}

export function formatRelative(value: string | null | undefined, now = Date.now()) {
  if (!value) return NO_DATA;
  const d = new Date(value).getTime();
  if (Number.isNaN(d)) return value;
  const diff = (d - now) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return relFmt.format(Math.round(diff), "second");
  if (abs < 3600) return relFmt.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return relFmt.format(Math.round(diff / 3600), "hour");
  return relFmt.format(Math.round(diff / 86400), "day");
}

export function formatDuration(ms: number | null | undefined) {
  if (ms === null || ms === undefined) return NO_DATA;
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1).replace(".", ",")} s`;
  return `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s`;
}

export function formatBool(v: boolean | null | undefined) {
  if (v === null || v === undefined) return NO_DATA;
  return v ? "tak" : "nie";
}

export function formatDistance(m: number) {
  return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1).replace(".", ",")} km`;
}

export const READINESS_LABEL: Record<string, string> = {
  ready: "Gotowy",
  attention: "Wymaga uwagi",
  expired: "Po terminie",
  unknown: "Brak danych serwisowych",
};

export const ACCESS_LABEL: Record<string, string> = {
  public: "Publiczny",
  limited: "Ograniczony",
  private: "Prywatny",
  unknown: "Nieznany",
};

export const OPERATIONAL_LABEL: Record<string, string> = {
  operational: "Sprawny",
  out_of_service: "Wyłączony z użytku",
  missing: "Zaginiony",
  decommissioned: "Wycofany",
  unknown: "Nieznany",
};

export const RUN_STATUS_LABEL: Record<string, string> = {
  queued: "W kolejce",
  running: "W toku",
  success: "Sukces",
  failed: "Błąd",
};

export const RUN_KIND_LABEL: Record<string, string> = {
  historical: "Historyczna",
  periodic: "Okresowa",
};

export const RUN_TRIGGER_LABEL: Record<string, string> = {
  seed: "Seed",
  schedule: "Harmonogram",
  manual: "Ręcznie",
};

export const EVENT_KIND_LABEL: Record<string, string> = {
  pads_replaced: "Wymiana elektrod",
  battery_replaced: "Wymiana baterii",
  inspection: "Przegląd",
  self_test: "Autotest",
  used_in_rescue: "Użycie w akcji ratunkowej",
  repair: "Naprawa",
  decommissioned: "Wycofanie z użytku",
};

export const CHANGE_OP_LABEL: Record<string, string> = {
  create: "nowy",
  update: "zmiana",
  remove: "usunięty",
  restore: "przywrócony",
};

export const ENUM_LABELS: Record<string, Record<string, string>> = {
  coordinate_method: {
    gps: "GPS",
    survey: "Pomiar w terenie",
    geocoded: "Geokodowanie adresu",
    source: "Ze źródła",
    unknown: "Nieznana",
  },
  cabinet: { alarm: "Z alarmem", open: "Otwarta", locked: "Zamknięta", none: "Brak", unknown: "Nieznana" },
  pads_type: { adult: "Dla dorosłych", pediatric: "Pediatryczne", universal: "Uniwersalne", unknown: "Nieznany" },
  battery_status: { ok: "Sprawna", low: "Słaba", replace: "Do wymiany", unknown: "Nieznany" },
  placement: {
    vehicle: "W pojeździe (np. wóz OSP)",
    inside_building: "Wewnątrz budynku",
    outside_on_building: "Na zewnętrznej ścianie budynku",
    freestanding_outdoor: "Wolnostojący, na zewnątrz",
    unknown: "Nieznane",
  },
  access_conditions: {
    ask_staff_or_security: "Wydaje personel lub ochrona",
    key_holder: "Klucz u wskazanej osoby",
    call_phone: "Trzeba zadzwonić",
    siren_or_alarm_button: "Najpierw syrena / przycisk alarmowy",
    only_during_opening_hours: "Tylko w godzinach otwarcia",
    only_during_events: "Tylko podczas wydarzeń",
    staff_only: "Tylko dla pracowników",
    other: "Inny warunek",
  },
  access: ACCESS_LABEL,
  operational_status: OPERATIONAL_LABEL,
  readiness: READINESS_LABEL,
};

export function label(map: Record<string, string>, value: string | null | undefined) {
  if (value === null || value === undefined || value === "") return NO_DATA;
  return map[value] ?? value;
}

export function formatBytes(n: number | null | undefined) {
  if (n === null || n === undefined) return NO_DATA;
  if (n < 1024) return `${n} B`;
  const units = ["kB", "MB", "GB"];
  let value = n / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value < 10 ? 1 : 0).replace(".", ",")} ${units[unit]}`;
}
