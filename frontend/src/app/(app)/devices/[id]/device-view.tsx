"use client";

import { AlertTriangleIcon, CheckIcon, CopyIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import {
  AccessBadge,
  CodeBlock,
  ErrorAlert,
  ExternalLink,
  Facts,
  LoadingRows,
  PageHeader,
  ReadinessBadge,
  Section,
} from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, type DeviceDetail } from "@/lib/api";
import {
  ENUM_LABELS,
  EVENT_KIND_LABEL,
  formatBool,
  formatDate,
  formatDateTime,
  formatNumber,
  label,
  NO_DATA,
} from "@/lib/format";
import { parseOpeningHours } from "@/lib/opening-hours";
import { useApi } from "@/lib/use-api";

import { DeviceJson } from "./device-json";
import { DeviceMap } from "./device-map";

type Kind =
  | "text"
  | "date"
  | "datetime"
  | "bool"
  | "number"
  | "opening_hours"
  | keyof typeof ENUM_LABELS;
type FieldSpec = [
  field: keyof DeviceDetail & string,
  label: string,
  kind?: Kind,
];
/** A card's fields, optionally split into named parts; a part with no data collapses into one "Brak danych" line. */
type Part = { title?: string; fields: FieldSpec[] };

const LOCATION: Part[] = [
  {
    fields: [
      ["building_name", "Obiekt"],
      ["address", "Adres"],
      ["postal_code", "Kod pocztowy"],
      ["city", "Miejscowość"],
      ["municipality", "Gmina"],
      ["location_detail", "Miejsce w obiekcie"],
      ["floor", "Piętro"],
      ["placement", "Umiejscowienie", "placement"],
      ["coordinate_method", "Współrzędne", "coordinate_method"],
      ["coordinate_accuracy_m", "Dokładność (m)", "number"],
    ],
  },
];

const ACCESS: Part[] = [
  {
    fields: [
      ["access", "Dostęp", "access"],
      ["opening_hours", "Godziny dostępności", "opening_hours"],
      ["opening_hours_raw", "Godziny — zapis źródłowy"],
      ["access_conditions", "Warunki dostępu", "access_conditions"],
      ["seasonal", "Dostępność sezonowa", "bool"],
      ["cabinet", "Szafka", "cabinet"],
    ],
  },
];

const READINESS: Part[] = [
  {
    title: "status",
    fields: [
      ["operational_status", "Status urządzenia", "operational_status"],
      ["verified_on", "Data weryfikacji", "date"],
      ["verification_method", "Sposób weryfikacji"],
    ],
  },
  {
    title: "elektrody",
    fields: [
      ["pads_type", "Rodzaj elektrod", "pads_type"],
      ["pads_expiry_date", "Elektrody ważne do", "date"],
      ["pads_replaced_on", "Ostatnia wymiana elektrod", "date"],
      ["pediatric_pads_available", "Elektrody pediatryczne", "bool"],
      ["pediatric_mode", "Tryb pediatryczny", "bool"],
    ],
  },
  {
    title: "bateria",
    fields: [
      ["battery_status", "Stan baterii", "battery_status"],
      ["battery_expiry_date", "Bateria ważna do", "date"],
      ["battery_installed_on", "Bateria zainstalowana", "date"],
    ],
  },
  {
    title: "przeglądy",
    fields: [
      ["last_inspection_on", "Ostatni przegląd", "date"],
      ["next_inspection_due", "Następny przegląd", "date"],
      ["last_self_test_at", "Ostatni autotest", "datetime"],
      ["last_self_test_result", "Wynik autotestu"],
      ["last_used_on", "Ostatnie użycie", "date"],
    ],
  },
];

const OPERATOR: Part[] = [
  {
    fields: [
      ["operator_name", "Nazwa"],
      ["operator_contact", "Kontakt (instytucjonalny)"],
      ["operator_regon", "REGON"],
    ],
  },
];

const HARDWARE: Part[] = [
  {
    fields: [
      ["manufacturer", "Producent"],
      ["model", "Model"],
      ["serial_number", "Numer seryjny"],
      ["inventory_number", "Numer inwentarzowy"],
      ["manufactured_on", "Data produkcji", "date"],
      ["installed_on", "Data instalacji", "date"],
      ["is_mobile", "Urządzenie mobilne", "bool"],
    ],
  },
];

const METADATA: FieldSpec[] = [
  ["teryt", "TERYT gminy"],
  ["simc", "SIMC"],
  ["created_at", "Utworzono", "datetime"],
  ["updated_at", "Zmieniono", "datetime"],
];

// Reference data that fills fields without being an integration (devices/boundaries.py)
const REFERENCE_SOURCES: Record<string, string> = {
  prg: "Granice administracyjne PRG (GUGiK)",
};

/** Empty, and also an enum's `unknown`: it says no more than an empty field. */
function isEmpty(value: unknown, kind: Kind = "text") {
  if (value === null || value === undefined || value === "") return true;
  if (Array.isArray(value))
    return value.length === 0 || value.every((v) => v === "unknown");
  return kind in ENUM_LABELS && value === "unknown";
}

function render(value: unknown, kind: Kind = "text"): React.ReactNode {
  if (isEmpty(value, kind)) return null;
  if (Array.isArray(value)) {
    return value
      .map((v) =>
        kind in ENUM_LABELS ? label(ENUM_LABELS[kind], String(v)) : String(v),
      )
      .join(", ");
  }
  switch (kind) {
    case "date":
      return formatDate(String(value));
    case "datetime":
      return formatDateTime(String(value));
    case "bool":
      return formatBool(value as boolean);
    case "number":
      return formatNumber(Number(value));
    case "text":
      return String(value);
    case "opening_hours":
      return <OpeningHours value={String(value)} />;
    default:
      return label(ENUM_LABELS[kind], String(value));
  }
}

/** The OSM `opening_hours` value as one line per rule; the source value when it can't be parsed. */
function OpeningHours({ value }: { value: string }) {
  const lines = parseOpeningHours(value, "pl");
  if (!lines) return value;
  const cap = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
  return (
    <ul className="space-y-0.5">
      {lines.map((line, i) => (
        <li key={i} className="tabular-nums">
          {line.when ? `${cap(line.when)}: ${line.what}` : cap(line.what)}
        </li>
      ))}
    </ul>
  );
}

/**
 * The device's values with redundant ones dropped: the source's free-text hours when they say the same as the
 * parsed ones, and "inside the building" when the placement already says where it is.
 */
function displayValues(d: DeviceDetail): Record<string, unknown> {
  const values: Record<string, unknown> = { ...d };
  if (d.opening_hours && d.opening_hours_raw?.trim() === d.opening_hours.trim())
    values.opening_hours_raw = null;
  if (isEmpty(d.placement, "placement") && d.indoor !== null) {
    values.placement = d.indoor ? "inside_building" : null;
  }
  return values;
}

/** What an admin should fill in first, in the order the brief asks: where, accessible now, does it work. */
function missingKeyData(d: DeviceDetail): string[] {
  const missing: string[] = [];
  if (!d.address) missing.push("adresu");
  if (d.indoor === true && !d.floor) missing.push("piętra");
  if (d.access === "unknown") missing.push("rodzaju dostępu");
  if (!d.opening_hours && !d.opening_hours_raw)
    missing.push("godzin dostępności");
  if (d.readiness === "unknown")
    missing.push("dat serwisowych (elektrody, bateria, przegląd)");
  if (!d.operator_contact) missing.push("kontaktu do dysponenta");
  return missing;
}

function FieldCard({
  title,
  parts,
  values,
  hint,
  showEmpty,
  actions,
  children,
  className,
}: {
  title: string;
  parts: Part[];
  values: Record<string, unknown>;
  hint: (field: string) => React.ReactNode;
  showEmpty: boolean;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  const items = (fields: FieldSpec[]) =>
    fields
      .filter(([field, , kind]) => showEmpty || !isEmpty(values[field], kind))
      .map(([field, text, kind]) => ({
        label: text,
        value: render(values[field], kind),
        hint: hint(field),
      }));
  const all = parts.map((p) => ({ ...p, items: items(p.fields) }));
  const filled = all.filter((p) => p.items.length > 0);
  const emptyParts = all.filter((p) => p.items.length === 0);
  const named = emptyParts.flatMap((p) => (p.title ? [p.title] : []));

  return (
    <Section title={title} actions={actions} className={className}>
      {filled.length > 0 ? (
        <div className="flex flex-col gap-4">
          {filled.map((p, i) =>
            parts.length > 1 && p.title ? (
              <div key={i}>
                <p className="type-micro mb-2 text-subtle-foreground uppercase">
                  {p.title}
                </p>
                <Facts items={p.items} />
              </div>
            ) : (
              <Facts key={i} items={p.items} />
            ),
          )}
        </div>
      ) : null}
      {emptyParts.length > 0 ? (
        <p
          className={`type-caption text-subtle-foreground italic ${filled.length > 0 ? "mt-4" : ""}`}
        >
          {named.length > 0
            ? `Brak danych: ${named.join(", ")}.`
            : "Brak danych."}
        </p>
      ) : null}
      {children}
    </Section>
  );
}

function CopyCoordinates({ lat, lon }: { lat: number; lon: number }) {
  const [copied, setCopied] = useState(false);
  const text = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Nie udało się skopiować do schowka.");
    }
  }
  return (
    <span className="inline-flex items-center gap-1">
      <span className="type-label text-subtle-foreground tabular-nums">
        {text}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        onClick={copy}
        aria-label="Kopiuj współrzędne"
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </Button>
    </span>
  );
}

export function DeviceView() {
  const { id } = useParams<{ id: string }>();
  const device = useApi(`device:${id}`, () => api.device(id));
  const [showEmpty, setShowEmpty] = useState(false);

  if (device.error && !device.data) return <ErrorAlert error={device.error} />;
  const d = device.data;
  if (!d) return <LoadingRows rows={10} />;

  const sourceName: Record<string, string> = {
    ...REFERENCE_SOURCES,
    ...Object.fromEntries(
      d.records.map((r) => [r.integration, r.integration_name]),
    ),
  };
  const singleSource = d.records.length === 1 ? d.records[0].integration : null;
  const values = displayValues(d);

  // Only what isn't obvious: values the AI read from a description, values derived from the coordinates, and, with
  // several sources, which one won. The full origin is in the tooltip.
  const hint = (field: string): React.ReactNode => {
    // The municipality name is looked up from the TERYT code, so it shares that code's origin
    const key =
      field === "municipality"
        ? "teryt"
        : field === "placement" && !d.placement
          ? "indoor"
          : field;
    const fs = d.field_sources?.[key];
    if (!fs) return undefined;
    const name = sourceName[fs.source] ?? fs.source;
    const origin = `${name} · ${formatDate(fs.seen)}`;
    if (fs.method === "inferred") {
      return (
        <span
          title={`Odczytane przez lokalny model AI z opisu w źródle: ${origin}`}
        >
          <Badge variant="outline" className="mr-1">
            AI
          </Badge>
          z opisu{singleSource ? "" : ` · ${name}`}
        </span>
      );
    }
    if (fs.method === "geocoded") {
      return (
        <span
          title={`Ustalone ze współrzędnych i urzędowych granic administracyjnych: ${origin}`}
        >
          <Badge variant="outline" className="mr-1">
            Geo
          </Badge>
          ze współrzędnych
        </span>
      );
    }
    return singleSource === fs.source ? undefined : (
      <span title={origin}>{name}</span>
    );
  };

  const allFields = [
    ...LOCATION,
    ...ACCESS,
    ...READINESS,
    ...OPERATOR,
    ...HARDWARE,
  ].flatMap((p) => p.fields);
  const emptyCount = allFields.filter(([field, , kind]) =>
    isEmpty(values[field], kind),
  ).length;
  const missing = missingKeyData(d);
  const osmRecord = d.records.find((r) =>
    /^(node|way|relation)\/\d+$/.test(r.source_record_id),
  );
  const title =
    d.name ?? d.building_name ?? d.operator_name ?? d.address ?? d.id;
  const place =
    [d.address, d.city].filter(Boolean).join(", ") || d.municipality;
  const cardProps = { values, hint, showEmpty };

  return (
    <>
      <PageHeader
        meta={
          <span className="type-caption flex flex-wrap items-center gap-x-2">
            <Link
              href="/devices"
              className="text-link hover:text-link-hover hover:underline"
            >
              ← Urządzenia
            </Link>
            {title !== d.id ? (
              <span className="font-mono text-muted-foreground">{d.id}</span>
            ) : null}
          </span>
        }
        title={title}
        description={
          [place, d.location_detail].filter(Boolean).join(" · ") || undefined
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ReadinessBadge value={d.readiness} />
            <AccessBadge value={d.access} />
            {!d.active ? <Badge variant="secondary">Nieaktywne</Badge> : null}
            <DeviceJson device={d} />
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 bg-card px-4 py-2 ring-1 ring-border">
        <CopyCoordinates lat={d.lat} lon={d.lon} />
        <Link
          href={`/map#${d.lat},${d.lon},17`}
          className="type-caption text-link hover:text-link-hover hover:underline"
        >
          Pokaż na mapie
        </Link>
        {osmRecord ? (
          <ExternalLink
            href={`https://www.openstreetmap.org/${osmRecord.source_record_id}`}
            className="type-caption"
          >
            Edytuj w OpenStreetMap ({osmRecord.source_record_id})
          </ExternalLink>
        ) : (
          <ExternalLink
            href={`https://www.openstreetmap.org/?mlat=${d.lat}&mlon=${d.lon}#map=19/${d.lat}/${d.lon}`}
            className="type-caption"
          >
            OpenStreetMap
          </ExternalLink>
        )}
        <label className="type-caption ml-auto flex cursor-pointer items-center gap-2 text-muted-foreground">
          <Switch
            size="sm"
            checked={showEmpty}
            onCheckedChange={setShowEmpty}
          />
          Pokaż puste pola ({emptyCount})
        </label>
      </div>

      {missing.length > 0 ? (
        <p className="type-body mb-6 flex items-start gap-2 bg-caution-subtle px-4 py-3 text-caution-subtle-foreground">
          <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            <span className="font-medium">Brakuje kluczowych danych:</span>{" "}
            {missing.join(", ")}.
          </span>
        </p>
      ) : null}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        <FieldCard title="Lokalizacja" parts={LOCATION} {...cardProps}>
          {d.photo_url ? (
            /* eslint-disable-next-line @next/next/no-img-element -- remote photos from arbitrary sources */
            <img
              src={d.photo_url}
              alt={`Zdjęcie AED: ${title}`}
              className="mt-4 max-h-64 max-w-full ring-1 ring-border"
            />
          ) : null}
        </FieldCard>

        <Section title="Mapa">
          <DeviceMap id={d.id} lat={d.lat} lon={d.lon} label={title} />
          <ul className="type-caption mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
            <li className="flex items-center gap-1.5">
              <span
                className="size-2.5 rounded-full bg-hn-crimson"
                aria-hidden
              />
              To urządzenie
            </li>
            <li className="flex items-center gap-1.5">
              <span
                className="size-2 rounded-full bg-muted-foreground"
                aria-hidden
              />
              Inne AED w pobliżu (kliknij, by otworzyć)
            </li>
          </ul>
        </Section>

        <FieldCard title="Dostęp" parts={ACCESS} {...cardProps} />

        <FieldCard
          title="Gotowość i serwis"
          parts={READINESS}
          {...cardProps}
          actions={
            <AddEvent deviceId={d.id} onAdded={() => void device.reload()} />
          }
        >
          <ServiceHistory events={d.events} />
        </FieldCard>

        <FieldCard title="Dysponent" parts={OPERATOR} {...cardProps} />
        <FieldCard title="Urządzenie" parts={HARDWARE} {...cardProps} />
      </div>

      <Section title="Źródła i metadane" className="mt-6">
        <Facts
          className="sm:grid-cols-4"
          items={METADATA.filter(
            ([field, , kind]) => showEmpty || !isEmpty(values[field], kind),
          ).map(([field, text, kind]) => ({
            label: text,
            value: render(values[field], kind),
            hint: hint(field),
          }))}
        />
        {singleSource ? (
          <p className="type-caption mt-4 text-muted-foreground">
            Pola bez oznaczenia pochodzą z jedynego źródła:{" "}
            {sourceName[singleSource]}.
          </p>
        ) : null}
        {d.records.length === 0 ? (
          <p className="type-caption mt-4 text-muted-foreground">
            Brak rekordów źródłowych.
          </p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {d.records.map((r) => (
              <li key={`${r.integration}:${r.source_record_id}`}>
                <details className="group bg-background ring-1 ring-border">
                  <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
                    {/* No links inside <summary> (nested interactive): the source link is in the open panel */}
                    <span className="font-medium">{r.integration_name}</span>
                    <span className="font-mono text-xs">
                      {r.source_record_id}
                    </span>
                    <span className="type-caption text-muted-foreground">
                      od {formatDate(r.first_seen)} · ostatnio{" "}
                      {formatDate(r.last_seen)}
                    </span>
                    {r.removed_at ? (
                      <Badge variant="secondary">
                        Usunięty ze źródła {formatDate(r.removed_at)}
                      </Badge>
                    ) : null}
                  </summary>
                  <p className="type-caption border-t border-border px-3 py-2">
                    <Link
                      href={`/integrations/${r.integration}`}
                      className="text-link underline underline-offset-2 hover:text-link-hover"
                    >
                      Źródło: {r.integration_name}
                    </Link>
                  </p>
                  <CodeBlock
                    value={r.data}
                    className="border-t border-border"
                  />
                  {Object.keys(r.inferred ?? {}).length > 0 ? (
                    <div className="border-t border-border">
                      <p className="type-caption px-3 pt-2 text-muted-foreground">
                        Odczytane z opisu przez lokalny model AI — używane tylko
                        tam, gdzie źródło nie podaje pola
                      </p>
                      <CodeBlock value={r.inferred} />
                    </div>
                  ) : null}
                </details>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </>
  );
}

function ServiceHistory({ events }: { events: DeviceDetail["events"] }) {
  return (
    <div className="mt-4 border-t border-border pt-4">
      <p className="type-micro mb-2 text-subtle-foreground uppercase">
        Historia serwisowa
      </p>
      {events.length === 0 ? (
        <p className="type-caption text-subtle-foreground italic">
          Brak zdarzeń serwisowych.
        </p>
      ) : (
        <ol className="relative border-l border-border pl-5">
          {[...events]
            .sort((a, b) => b.date.localeCompare(a.date))
            .map((e) => (
              <li key={e.id} className="mb-4 last:mb-0">
                <span
                  className="absolute -left-[5px] mt-1.5 size-2.5 bg-primary"
                  aria-hidden
                />
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <span className="type-h4">
                    {label(EVENT_KIND_LABEL, e.kind)}
                  </span>
                  <span className="type-label text-subtle-foreground">
                    {formatDate(e.date)}
                  </span>
                </div>
                {e.details ? (
                  <p className="type-body mt-0.5">{e.details}</p>
                ) : null}
                <p className="type-caption mt-0.5 text-muted-foreground">
                  {e.next_due ? (
                    <>Następny termin: {formatDate(e.next_due)} · </>
                  ) : null}
                  źródło: {e.source || NO_DATA}
                  {e.reported_by ? <> · zgłosił(a): {e.reported_by}</> : null}
                </p>
              </li>
            ))}
        </ol>
      )}
    </div>
  );
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function AddEvent({
  deviceId,
  onAdded,
}: {
  deviceId: string;
  onAdded: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState("inspection");
  const [date, setDate] = useState(today);
  const [nextDue, setNextDue] = useState("");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.addEvent(deviceId, {
        kind,
        date,
        details: details.trim() || undefined,
        next_due: nextDue || null,
      });
      toast.success("Dodano zdarzenie serwisowe.");
      setDetails("");
      setNextDue("");
      setOpen(false);
      onAdded();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <PlusIcon data-icon="inline-start" />
          Dodaj zdarzenie
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Dodaj zdarzenie serwisowe</DialogTitle>
            <DialogDescription>
              Wymiana elektrod lub baterii, przegląd albo użycie urządzenia.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ev-kind">Rodzaj</Label>
            <NativeSelect
              id="ev-kind"
              className="w-full"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              {Object.entries(EVENT_KIND_LABEL).map(([v, l]) => (
                <NativeSelectOption key={v} value={v}>
                  {l}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ev-date">Data</Label>
              <Input
                id="ev-date"
                type="date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ev-next">Następny termin (opcjonalnie)</Label>
              <Input
                id="ev-next"
                type="date"
                value={nextDue}
                onChange={(e) => setNextDue(e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ev-details">Szczegóły</Label>
            <Textarea
              id="ev-details"
              rows={3}
              placeholder="Np. elektrody Philips M5071A, partia 2026-08"
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Anuluj
            </Button>
            <Button type="submit" disabled={busy || !date}>
              Zapisz zdarzenie
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
