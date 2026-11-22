/**
 * Typed client for the Django API (docs/api.md). Next proxies /api/* to Django, so every call is same-origin and the
 * session cookie rides along. Unsafe methods carry the CSRF token from the `csrftoken` cookie.
 */

export type Readiness = "ready" | "attention" | "expired" | "unknown";
export type Access = "public" | "limited" | "private" | "unknown";
export type OperationalStatus =
  "operational" | "out_of_service" | "missing" | "decommissioned" | "unknown";
export type RunKind = "historical" | "periodic";
export type RunStatus = "queued" | "running" | "success" | "failed";
export type EventKind =
  | "pads_replaced"
  | "battery_replaced"
  | "inspection"
  | "self_test"
  | "used_in_rescue"
  | "repair"
  | "decommissioned";

export type Stats = {
  devices: number;
  active_devices: number;
  /** Active devices that have each piece of what a rescuer needs (absent in responses cached before it existed). */
  completeness?: {
    address: number;
    location_detail: number;
    access_known: number;
    opening_hours: number;
    maintenance: number;
    verified: number;
    operator?: number;
    photo?: number;
  };
  by_placement?: Record<"inside_building" | "outside_on_building" | "freestanding_outdoor" | "vehicle" | "unknown", number>;
  verification_age?: { last_year: number; one_to_three_years: number; older: number; never: number };
  by_source_count?: { one: number; two: number; three_or_more: number };
  by_readiness: Record<Readiness, number>;
  by_access: Record<Access, number>;
  with_maintenance_data: number;
  multi_source: number;
  pending_matches: number;
  sources: {
    slug: string;
    name: string;
    records: number;
    valid_records: number;
    last_success_at: string | null;
  }[];
  data_version: number;
  generated_at: string;
};

export type Source = {
  slug: string;
  name: string;
  publisher: string;
  source_url: string;
  homepage_url: string;
  attribution: string;
  records: number;
  last_success_at: string | null;
};

export type DeviceListItem = {
  id: string;
  lat: number;
  lon: number;
  name: string | null;
  address: string | null;
  city: string | null;
  access: Access;
  readiness: Readiness;
  operational_status: OperationalStatus;
  active: boolean;
  source_count: number;
  sources: string[];
  verified_on: string | null;
};

export type MaintenanceEvent = {
  id: number;
  kind: EventKind | string;
  date: string;
  details: string;
  next_due: string | null;
  source: string;
  reported_by: string;
  created_at: string;
};

type Nullable<T> = T | null;

export type DeviceDetail = DeviceListItem & {
  serial_number: Nullable<string>;
  manufacturer: Nullable<string>;
  model: Nullable<string>;
  inventory_number: Nullable<string>;
  manufactured_on: Nullable<string>;
  installed_on: Nullable<string>;
  coordinate_method: Nullable<string>;
  coordinate_accuracy_m: Nullable<number>;
  postal_code: Nullable<string>;
  teryt: Nullable<string>;
  // Display name of the municipality with that TERYT code ("gmina wiejska Zawoja"), from the PRG boundaries
  municipality: Nullable<string>;
  simc: Nullable<string>;
  building_name: Nullable<string>;
  location_detail: Nullable<string>;
  floor: Nullable<string>;
  indoor: Nullable<boolean>;
  placement: Nullable<string>;
  opening_hours: Nullable<string>;
  opening_hours_raw: Nullable<string>;
  access_conditions: Nullable<string[]>;
  seasonal: Nullable<boolean>;
  cabinet: Nullable<string>;
  is_mobile: Nullable<boolean>;
  photo_url: Nullable<string>;
  pads_type: Nullable<string>;
  pads_replaced_on: Nullable<string>;
  pads_expiry_date: Nullable<string>;
  pediatric_pads_available: Nullable<boolean>;
  pediatric_mode: Nullable<boolean>;
  battery_installed_on: Nullable<string>;
  battery_expiry_date: Nullable<string>;
  battery_status: Nullable<string>;
  last_self_test_at: Nullable<string>;
  last_self_test_result: Nullable<string>;
  last_inspection_on: Nullable<string>;
  next_inspection_due: Nullable<string>;
  last_used_on: Nullable<string>;
  verification_method: Nullable<string>;
  operator_name: Nullable<string>;
  operator_regon: Nullable<string>;
  operator_contact: Nullable<string>;
  // method "inferred": no source states the field; a local LLM read it from the source's free text.
  // method "geocoded" (source "prg"): teryt / city from the coordinates and the official boundaries (PRG, GUGiK).
  field_sources: Record<
    string,
    { source: string; seen: string; method?: "inferred" | "geocoded" }
  >;
  records: {
    integration: string;
    integration_name: string;
    source_record_id: string;
    first_seen: string;
    last_seen: string;
    removed_at: string | null;
    data: Record<string, unknown>;
    inferred: Record<string, unknown>;
  }[];
  events: MaintenanceEvent[];
  created_at: string;
  updated_at: string;
};

export type SchemaField = {
  field: string;
  label: string;
  type: string;
  level: 1 | 2 | 3;
  example: string;
  note: string;
};

/** A file as dane.gov.pl describes a resource; `link` is what gets registered on the portal. */
export type ExportResource = {
  title: string;
  description: string;
  format: string;
  media_type: "file" | "api";
  export?: string;
  version_link?: string | null;
  path: string;
  link: string;
  content_type: string;
  file_size?: number;
  etag?: string;
  availability?: "local" | "remote";
  data_date: string;
  language: string;
  openness_score?: number;
  contains_protected_data?: boolean;
  has_dynamic_data?: boolean;
  has_high_value_data?: boolean;
  has_high_value_data_from_ec_list?: boolean;
  has_research_data?: boolean;
  is_auto_data_date?: boolean;
  data_date_update_period?: "daily" | "weekly" | "monthly";
  endless_data_date_update?: boolean;
};

/** GET /api/export/dataset.json — dataset metadata in dane.gov.pl's shape (API 1.4 dataset / resource attributes). */
export type DatasetExport = {
  dataset: {
    title: string;
    notes: string;
    keywords: string[];
    categories: { code: string; title: string }[];
    /** dane.gov.pl code: daily, weekly, monthly, quarterly, everyHalfYear, yearly, irregular, notPlanned */
    update_frequency: string;
    update_frequency_label: string;
    regions: { name: string }[];
    language: string;
    license_name: string;
    license_url: string;
    license_condition_custom_description: string;
    /** the portal licence chosen (CC0 1.0 / CC BY 4.0 / CC BY-SA 4.0), null until decided */
    license_chosen: string | null;
    url: string;
    contains_protected_data: boolean;
    has_dynamic_data: boolean;
    has_high_value_data: boolean;
    has_high_value_data_from_ec_list: boolean;
    has_research_data: boolean;
    modified: string;
    data_date: string;
  };
  resources: ExportResource[];
  supplements: ExportResource[];
  /** Our list of protected data (DGA): a second dataset in harvester.xml, copied by the portal into its national list. */
  dga: {
    dataset: { title: string; notes: string; url: string; update_frequency: string; modified: string; data_date: string };
    resources: ExportResource[];
  };
  sources: {
    slug: string;
    name: string;
    publisher: string;
    homepage_url: string;
    license: string;
    license_url: string;
    attribution: string;
  }[];
  metadata: {
    records: number;
    fields: number;
    schema_url: string;
    page_url: string;
    generated_at: string;
    data_version: number;
  };
};

/** One cell of the coverage matrix: records that fill the field, and their share (null when there are none). */
export type CoverageCell = { count: number; pct: number | null };

/** GET /api/sources/coverage — per field of the reference scope, how much each source and the merged set fill. */
export type SourceCoverage = {
  levels: { level: 1 | 2 | 3; label: string }[];
  sources: { slug: string; name: string; publisher: string; priority: number; records: number }[];
  merged: { records: number };
  fields: {
    field: string;
    label: string;
    level: 1 | 2 | 3;
    /** null: the merge sets this field, no source does (id, readiness, sources) */
    sources: Record<string, CoverageCell | null>;
    merged: CoverageCell & { by_source: { source: string; method: string; count: number }[] };
  }[];
  data_version: number;
  generated_at: string;
};

export type SyncRun = {
  id: number;
  integration: string;
  integration_name: string;
  kind: RunKind | string;
  trigger: string;
  status: RunStatus | string;
  dry_run: boolean;
  reextract?: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  fetched: number;
  created: number;
  updated: number;
  unchanged: number;
  removed: number;
  invalid: number;
  error: string;
  snapshot_sha256: string;
  details: {
    changes?: {
      op: "create" | "update" | "remove" | "restore";
      source_record_id: string;
      fields?: string[];
    }[];
    issues?: { source_record_id: string; issues: string[] }[];
    truncated?: boolean;
    enrichment?: EnrichmentStats;
    merge?: Record<string, number>;
  };
};

/** What the LLM step of a run reports at the end (`details.enrichment`). */
export type EnrichmentStats = {
  model?: string;
  prompt_version?: string;
  inputs?: number;
  cache_hits?: number;
  llm_calls?: number;
  failed?: number;
  skipped?: number;
  problem?: string;
  seconds?: number;
  fresh?: boolean;
  records?: number;
  records_updated?: number;
  records_to_extract?: number;
};

export type LivePhase = "queued" | "fetch" | "validate" | "diff" | "classify" | "write" | "done";

export type LiveTallies = {
  placement: Record<string, number>;
  access_conditions: Record<string, number>;
  opening_hours: number;
  floor: number;
  seasonal: number;
};

/** One LLM answer as the live view shows it: the free text it read and the fields it returned. */
export type LiveEvent = {
  seq: number;
  kind: "ok" | "failed" | "cache";
  source_record_id: string;
  records: number;
  input: Record<string, string>;
  output: Record<string, unknown>;
  error: string;
  ms: number;
  source_wins: string[];
};

export type RunLive = {
  run: SyncRun;
  live: {
    phase: LivePhase;
    phases: Partial<Record<LivePhase, string>>;
    status: string;
    error: string;
    total: number;
    records: number;
    llm_calls: number;
    done: number;
    cache_hits: number;
    failed: number;
    ms_total: number;
    elapsed: number;
    throughput: [number, number][];
    tallies: LiveTallies;
    seq: number;
  };
  events: LiveEvent[];
  summary: { enrichment: EnrichmentStats; merge: Record<string, number> | null } | null;
};

export type EnrichmentStatus = {
  enabled: boolean;
  model: string;
  prompt_version: string;
  concurrency: number;
  problem: string;
  sources: { slug: string; name: string; with_text: number }[];
};

/** A run as the integrations list shows it in the health strip. */
export type RunBrief = Pick<SyncRun, "id" | "kind" | "status" | "dry_run" | "created_at" | "error">;

export type Integration = {
  slug: string;
  name: string;
  connector: string;
  description: string;
  publisher: string;
  source_url: string;
  homepage_url: string;
  attribution: string;
  format: string;
  enabled: boolean;
  periodic_enabled: boolean;
  sync_interval_hours: number;
  priority: number;
  config: Record<string, unknown>;
  accepts_upload: boolean;
  historical_completed_at: string | null;
  next_run_at: string | null;
  last_success_at: string | null;
  last_run: SyncRun | null;
  /** The latest runs, newest first (up to 12). */
  recent_runs: RunBrief[];
  running: boolean;
  records: number;
  valid_records: number;
  invalid_records: number;
  removed_records: number;
  devices: number;
};

type IntegrationText = Pick<
  Integration,
  | "name"
  | "description"
  | "publisher"
  | "source_url"
  | "homepage_url"
  | "attribution"
>;

/** Only operator integrations are created in the UI; fetched feeds are connector classes in the backend. */
export type IntegrationCreate = Partial<
  Pick<
    Integration,
    "description" | "publisher" | "homepage_url" | "attribution"
  >
> & {
  name: string;
  connector: "operator_file";
};

/** What an admin may change. Priority and interval are declared on the connector class (redeploy to change). */
export type IntegrationUpdate = Partial<
  IntegrationText & Pick<Integration, "enabled" | "periodic_enabled" | "config">
>;

export type SourceRecord = {
  id: number;
  source_record_id: string;
  lat: number | null;
  lon: number | null;
  is_valid: boolean;
  issues: string[];
  data: Record<string, unknown>;
  raw: Record<string, unknown>;
  inferred: Record<string, unknown>;
  first_seen: string;
  last_seen: string;
  removed_at: string | null;
  device_id: string | null;
};

export type Match = {
  id: number;
  distance_m: number;
  status: string;
  reason: string;
  created_at: string;
  device_a: DeviceListItem;
  device_b: DeviceListItem;
};

/** One AED from GET /api/aed/nearby: the public reference record (as in the exports), distance, availability, links. */
export type NearbyAed = {
  distance_m: number;
  aed: {
    id: string;
    lat: number;
    lon: number;
    address: string | null;
    postal_code: string | null;
    city: string | null;
    municipality: string | null;
    access: Access;
    operational_status: OperationalStatus;
    readiness: Readiness;
    verified_on: string | null;
    verification_method: string | null;
    sources: string[];
    building_name: string | null;
    location_detail: string | null;
    floor: string | null;
    indoor: boolean | null;
    placement: string | null;
    opening_hours: string | null;
    opening_hours_raw: string | null;
    access_conditions: string[] | null;
    cabinet: string | null;
    pads_expiry_date: string | null;
    battery_expiry_date: string | null;
    next_inspection_due: string | null;
    operator_name: string | null;
    operator_contact: string | null;
    updated_at: string | null;
  };
  /** Server-side `openingState` at request time (backend/devices/availability.py); the page recomputes it live. */
  availability: {
    state: "open" | "closed" | "unknown";
    open_24_7: boolean;
    until: string | null;
    next_open: string | null;
    reason: "none" | "unparsed" | "uncertain" | null;
    checked_at: string;
  };
  links: { self: string | null; record: string; map: string; directions: string };
};

export type Nearby = { query: { lat: number; lon: number }; items: NearbyAed[] };

export type Page<T> = { count: number; items: T[] };

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
}

function cookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

let csrfRequest: Promise<void> | null = null;

async function ensureCsrf(): Promise<string | null> {
  if (!cookie("csrftoken")) {
    csrfRequest ??= fetch("/api/auth/csrf", {
      credentials: "same-origin",
    }).then(() => undefined);
    await csrfRequest;
    csrfRequest = null;
  }
  return cookie("csrftoken");
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return detail
        .map((d) =>
          typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d),
        )
        .join("; ");
  }
  return fallback;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
  /** Send the person to /login on 401 (default). Off for the auth calls themselves. */
  redirectOn401?: boolean;
};

export async function request<T>(
  path: string,
  { method = "GET", body, form, redirectOn401 = true }: RequestOptions = {},
) {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    const token = await ensureCsrf();
    if (token) headers["X-CSRFToken"] = token;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError(0, "Brak połączenia z serwerem API.");
  }

  if (
    response.status === 401 &&
    redirectOn401 &&
    typeof window !== "undefined"
  ) {
    if (window.location.pathname !== "/login") {
      const next = window.location.pathname + window.location.search;
      window.location.replace(`/login?next=${encodeURIComponent(next)}`);
    }
    throw new ApiError(401, "Zaloguj się, aby kontynuować.");
  }
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;
  }
  if (!response.ok) {
    const fallback =
      response.status >= 500
        ? `Błąd serwera (${response.status}).`
        : `Żądanie odrzucone (${response.status}).`;
    throw new ApiError(response.status, detailOf(parsed, fallback));
  }
  return parsed as T;
}

function query(
  params: Record<string, string | number | boolean | null | undefined>,
) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  csrf: () =>
    request<{ csrfToken: string }>("/api/auth/csrf", { redirectOn401: false }),
  login: (email: string, password: string) =>
    request<{ email: string }>("/api/auth/login", {
      method: "POST",
      body: { email, password },
      redirectOn401: false,
    }),
  logout: () =>
    request<void>("/api/auth/logout", { method: "POST", redirectOn401: false }),
  me: () =>
    request<{ email: string }>("/api/auth/me", { redirectOn401: false }),

  stats: () => request<Stats>("/api/stats"),
  sources: () => request<Source[]>("/api/sources"),
  sourceCoverage: () => request<SourceCoverage>("/api/sources/coverage"),
  nearby: (p: { lat: number; lon: number; limit?: number; access?: string }) =>
    request<Nearby>(`/api/aed/nearby${query(p)}`),
  devices: (p: {
    q?: string;
    readiness?: string;
    access?: string;
    source?: string;
    bbox?: string;
    limit?: number;
    offset?: number;
  }) => request<Page<DeviceListItem>>(`/api/devices${query(p)}`),
  devicesPath: (p: Record<string, string | number | undefined>) =>
    `/api/devices${query(p)}`,
  device: (id: string) =>
    request<DeviceDetail>(`/api/devices/${encodeURIComponent(id)}`),
  addEvent: (
    id: string,
    body: {
      kind: string;
      date: string;
      details?: string;
      next_due?: string | null;
    },
  ) =>
    request<MaintenanceEvent>(`/api/devices/${encodeURIComponent(id)}/events`, {
      method: "POST",
      body,
    }),
  schema: () => request<SchemaField[]>("/api/schema"),
  dataset: () => request<DatasetExport>("/api/export/dataset.json"),

  integrations: () => request<Integration[]>("/api/integrations"),
  integration: (slug: string) =>
    request<Integration>(`/api/integrations/${slug}`),
  createIntegration: (body: IntegrationCreate) =>
    request<Integration>("/api/integrations", { method: "POST", body }),
  updateIntegration: (slug: string, body: IntegrationUpdate) =>
    request<Integration>(`/api/integrations/${slug}`, {
      method: "PATCH",
      body,
    }),
  sync: (
    slug: string,
    body: { kind: RunKind; dry_run?: boolean; force?: boolean; reextract?: boolean },
  ) =>
    request<SyncRun>(`/api/integrations/${slug}/sync`, {
      method: "POST",
      body,
    }),
  upload: (slug: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Integration>(`/api/integrations/${slug}/upload`, {
      method: "POST",
      form,
    });
  },
  integrationRuns: (slug: string, p: { limit?: number; offset?: number } = {}) =>
    request<Page<SyncRun>>(`/api/integrations/${slug}/runs${query(p)}`),
  records: (
    slug: string,
    p: { valid?: string; q?: string; limit?: number; offset?: number },
  ) =>
    request<Page<SourceRecord>>(`/api/integrations/${slug}/records${query(p)}`),
  runs: (limit = 50) => request<SyncRun[]>(`/api/runs${query({ limit })}`),
  run: (id: number) => request<SyncRun>(`/api/runs/${id}`),
  runLive: (id: number, after = 0) => request<RunLive>(`/api/runs/${id}/live${query({ after })}`),
  enrichment: () => request<EnrichmentStatus>("/api/enrichment"),
  matches: (p: { status?: string; limit?: number; offset?: number }) =>
    request<Page<Match>>(`/api/matches${query(p)}`),
  acceptMatch: (id: number) =>
    request<Match>(`/api/matches/${id}/accept`, { method: "POST" }),
  rejectMatch: (id: number) =>
    request<Match>(`/api/matches/${id}/reject`, { method: "POST" }),
};

export const EXPORTS = [
  {
    href: "/api/export/aeds.geojson",
    label: "GeoJSON",
    note: "Punkty z atrybutami, EPSG:4326",
  },
  {
    href: "/api/export/aeds.csv",
    label: "CSV",
    note: "Wzorcowy zakres danych, UTF-8",
  },
  { href: "/api/export/aeds.json", label: "JSON", note: "Pełne rekordy" },
  {
    href: "/api/export/aeds.jsonld",
    label: "JSON-LD",
    note: "Dane powiązane, schema.org",
  },
  {
    href: "/api/export/schema.xlsx",
    label: "Schemat XLSX",
    note: "Wzorcowy zakres danych",
  },
  {
    href: "/api/export/harvester.xml",
    label: "Harvester XML",
    note: "Import automatyczny dane.gov.pl",
  },
] as const;

// ---------------------------------------------------------------- reports (public form /zglos, admin inbox)

export type ReportKind =
  | "missing_aed"
  | "wrong_location"
  | "wrong_details"
  | "not_working"
  | "locked"
  | "holder_update";
export type ReportStatus = "new" | "in_review" | "resolved" | "rejected";

export const REPORT_KIND_LABEL: Record<ReportKind, string> = {
  missing_aed: "Brakujący AED",
  wrong_location: "Złe położenie",
  wrong_details: "Błędne dane (godziny, dostęp, opis)",
  not_working: "AED nie działa / brak elektrod",
  locked: "AED zamknięty / niedostępny",
  holder_update: "Jestem dysponentem i chcę przekazać dane",
};

export const REPORT_STATUS_LABEL: Record<ReportStatus, string> = {
  new: "Nowe",
  in_review: "W trakcie",
  resolved: "Załatwione",
  rejected: "Odrzucone",
};

export type ReportIn = {
  kind: ReportKind;
  device_id?: string | null;
  lat?: number | null;
  lon?: number | null;
  description: string;
  contact_email?: string | null;
  /** Honeypot: stays empty for people. */
  website?: string;
};

export type Report = {
  id: number;
  kind: ReportKind;
  kind_label: string;
  status: ReportStatus;
  device: {
    id: string;
    name: string | null;
    address: string | null;
    city: string | null;
    lat: number;
    lon: number;
  } | null;
  lat: number | null;
  lon: number | null;
  description: string;
  contact_email: string;
  admin_note: string;
  created_at: string;
  updated_at: string;
};

export type ReportPage = Page<Report> & { counts: Record<ReportStatus, number> };

/** Field errors from POST /api/reports (400): `errors` maps a form field to a Polish message. */
export class ReportError extends ApiError {
  constructor(
    status: number,
    detail: string,
    public errors: Record<string, string>,
  ) {
    super(status, detail);
  }
}

export const reportsApi = {
  /** Public, no login. Throws ReportError with per-field messages on 400. */
  create: async (body: ReportIn) => {
    let response: Response;
    try {
      response = await fetch("/api/reports", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
    } catch {
      throw new ReportError(0, "Brak połączenia z serwerem. Sprawdź internet i spróbuj ponownie.", {});
    }
    const parsed = (await response.json().catch(() => null)) as {
      detail?: unknown;
      errors?: Record<string, string>;
    } | null;
    if (!response.ok) {
      const detail =
        typeof parsed?.detail === "string"
          ? parsed.detail
          : response.status >= 500
            ? "Błąd serwera. Spróbuj ponownie za chwilę."
            : "Nie udało się wysłać zgłoszenia.";
      throw new ReportError(response.status, detail, parsed?.errors ?? {});
    }
    return parsed as { received: true };
  },
  list: (p: { status?: ReportStatus | ""; limit?: number; offset?: number }) =>
    request<ReportPage>(`/api/reports${query(p)}`),
  update: (id: number, body: { status?: ReportStatus; admin_note?: string }) =>
    request<Report>(`/api/reports/${id}`, { method: "PATCH", body }),
  remove: (id: number) => request<void>(`/api/reports/${id}`, { method: "DELETE" }),
};
