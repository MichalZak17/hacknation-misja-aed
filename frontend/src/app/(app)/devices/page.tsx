"use client";

import Link from "next/link";
import { useState } from "react";

import {
  AccessBadge,
  EmptyState,
  ErrorAlert,
  LoadingRows,
  PageHeader,
  Pager,
  ReadinessBadge,
} from "@/components/app/ui";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import {
  ACCESS_LABEL,
  formatDate,
  OPERATIONAL_LABEL,
  READINESS_LABEL,
  label,
} from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { useDebounced } from "@/lib/use-debounced";

const LIMIT = 50;

export default function DevicesPage() {
  const [q, setQ] = useState("");
  const [readiness, setReadiness] = useState("");
  const [access, setAccess] = useState("");
  const [source, setSource] = useState("");
  const [offset, setOffset] = useState(0);
  const query = useDebounced(q);

  const sources = useApi("sources", api.sources);
  const params = { q: query, readiness, access, source, limit: LIMIT, offset };
  const devices = useApi(JSON.stringify(params), () => api.devices(params));

  const reset =
    <T,>(set: (v: T) => void) =>
    (v: T) => {
      set(v);
      setOffset(0);
    };

  return (
    <>
      <PageHeader title="Urządzenia" />

      <div className="mb-4 grid grid-cols-1 gap-3 bg-card p-4 ring-1 ring-border sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-q">Szukaj</Label>
          <Input
            id="dev-q"
            type="search"
            placeholder="Nazwa, adres, miasto, ID, nr seryjny"
            value={q}
            onChange={(e) => reset(setQ)(e.target.value)}
          />
        </div>
        <FilterSelect
          id="dev-readiness"
          label="Gotowość"
          value={readiness}
          onChange={reset(setReadiness)}
          options={READINESS_LABEL}
        />
        <FilterSelect
          id="dev-access"
          label="Dostęp"
          value={access}
          onChange={reset(setAccess)}
          options={ACCESS_LABEL}
        />
        <FilterSelect
          id="dev-source"
          label="Źródło"
          value={source}
          onChange={reset(setSource)}
          options={Object.fromEntries(
            (sources.data ?? []).map((s) => [s.slug, s.name]),
          )}
        />
      </div>

      {devices.error ? <ErrorAlert error={devices.error} /> : null}
      {!devices.data ? (
        <LoadingRows rows={10} />
      ) : devices.data.items.length === 0 ? (
        <EmptyState
          title="Nic nie znaleziono"
          description="Zmień filtry albo wyszukiwaną frazę."
        />
      ) : (
        <div className="bg-card p-4 ring-1 ring-border">
          <div
            className={
              devices.loading
                ? "opacity-60 transition-opacity"
                : "transition-opacity"
            }
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Urządzenie</TableHead>
                  <TableHead>Miejscowość</TableHead>
                  <TableHead>Dostęp</TableHead>
                  <TableHead>Gotowość</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Źródła</TableHead>
                  <TableHead>Weryfikacja</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.data.items.map((d) => (
                  <TableRow
                    key={d.id}
                    className={d.active ? undefined : "opacity-60"}
                  >
                    <TableCell className="max-w-80">
                      <Link
                        href={`/devices/${encodeURIComponent(d.id)}`}
                        className="block truncate font-medium text-link hover:text-link-hover hover:underline"
                      >
                        {d.name ?? d.address ?? d.id}
                      </Link>
                      <div className="type-caption truncate text-muted-foreground">
                        <span className="font-mono">{d.id}</span>
                        {d.name && d.address ? <> · {d.address}</> : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      {d.city ?? (
                        <span className="text-subtle-foreground italic">
                          brak danych
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <AccessBadge value={d.access} />
                    </TableCell>
                    <TableCell>
                      <ReadinessBadge value={d.readiness} />
                    </TableCell>
                    <TableCell>
                      {label(OPERATIONAL_LABEL, d.operational_status)}
                    </TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      title={d.sources.join(", ")}
                    >
                      {d.source_count}
                    </TableCell>
                    <TableCell>{formatDate(d.verified_on)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pager
            count={devices.data.count}
            limit={LIMIT}
            offset={offset}
            onChange={setOffset}
          />
        </div>
      )}
    </>
  );
}

function FilterSelect({
  id,
  label: text,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: Record<string, string>;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{text}</Label>
      <NativeSelect
        id={id}
        className="w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <NativeSelectOption value="">Wszystkie</NativeSelectOption>
        {Object.entries(options).map(([v, l]) => (
          <NativeSelectOption key={v} value={v}>
            {l}
          </NativeSelectOption>
        ))}
      </NativeSelect>
    </div>
  );
}
