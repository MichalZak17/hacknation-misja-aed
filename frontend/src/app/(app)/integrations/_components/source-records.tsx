"use client";

import Link from "next/link";
import { Fragment, useState } from "react";
import { ChevronRightIcon } from "lucide-react";

import { CodeBlock, EmptyState, ErrorAlert, LoadingRows, Pager } from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type SourceRecord } from "@/lib/api";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { issueText } from "@/lib/integrations";
import { useDebounced } from "@/lib/use-debounced";
import { cn } from "@/lib/utils";

const LIMIT = 50;

/** What the source sent, record by record: the stored values, the raw input and what the AI read from free text. */
export function SourceRecords({ slug, invalid }: { slug: string; invalid: number }) {
  const [valid, setValid] = useState<"" | "true" | "false">("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<number | null>(null);
  const query = useDebounced(q);
  const records = useApi(`rec:${slug}:${valid}:${query}:${offset}`, () =>
    api.records(slug, { valid, q: query, limit: LIMIT, offset }),
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <SegmentedControl
          label="Pokaż rekordy"
          value={valid === "" ? "all" : valid}
          onValueChange={(v) => {
            setValid(v === "all" ? "" : (v as "true" | "false"));
            setOffset(0);
          }}
          options={[
            { value: "all", label: "Wszystkie" },
            { value: "true", label: "Poprawne" },
            { value: "false", label: invalid ? `Błędne (${invalid})` : "Błędne" },
          ]}
        />
        <Label htmlFor="rec-q" className="sr-only">
          Szukaj w rekordach
        </Label>
        <Input
          id="rec-q"
          type="search"
          placeholder="Szukaj po ID, nazwie lub adresie"
          className="h-8 w-full sm:ml-auto sm:w-72"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      {records.error ? <ErrorAlert error={records.error} /> : null}
      {!records.data ? (
        <LoadingRows />
      ) : records.data.items.length === 0 ? (
        <EmptyState
          title={q || valid ? "Nic nie pasuje" : "Brak rekordów"}
          description={q || valid ? "Zmień wyszukiwanie albo filtr." : "Rekordy pojawią się po pierwszym imporcie."}
        />
      ) : (
        <>
          <div className={cn("transition-opacity", records.loading && "opacity-60")}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID w źródle</TableHead>
                  <TableHead>Opis ze źródła</TableHead>
                  <TableHead className="max-md:hidden">Współrzędne</TableHead>
                  <TableHead>Urządzenie</TableHead>
                  <TableHead className="max-lg:hidden">Widziany</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.data.items.map((r) => (
                  <Fragment key={r.id}>
                    <RecordRow record={r} open={open === r.id} onToggle={() => setOpen(open === r.id ? null : r.id)} />
                    {open === r.id ? (
                      <TableRow className="hover:bg-transparent">
                        <TableCell colSpan={5} className="bg-canvas p-3 whitespace-normal">
                          <div id={`rec-${r.id}`} className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <JsonBlock title="Zapisane (po normalizacji)" value={r.data} />
                            <JsonBlock title="Tak jak przyszło ze źródła" value={r.raw} />
                            {Object.keys(r.inferred ?? {}).length > 0 ? (
                              <JsonBlock title="Odczytane z opisu przez AI (niższy priorytet niż dane źródła)" value={r.inferred} />
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pager count={records.data.count} limit={LIMIT} offset={offset} onChange={setOffset} />
        </>
      )}
    </div>
  );
}

function str(v: unknown) {
  return typeof v === "string" && v.trim() ? v : null;
}

function RecordRow({ record: r, open, onToggle }: { record: SourceRecord; open: boolean; onToggle: () => void }) {
  const name = str(r.data.building_name) ?? str(r.data.name) ?? str(r.data.location_detail);
  const address = [str(r.data.address), str(r.data.city)].filter(Boolean).join(", ");
  return (
    <TableRow className={cn(r.removed_at && "text-muted-foreground", open && "bg-selected")}>
      <TableCell>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={`rec-${r.id}`}
          onClick={onToggle}
          className="inline-flex items-center gap-1 font-mono text-xs outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <ChevronRightIcon aria-hidden className={cn("size-3.5 transition-transform duration-200 ease-standard", open && "rotate-90")} />
          {r.source_record_id}
        </button>
      </TableCell>
      <TableCell className="max-w-80 whitespace-normal">
        <div className="truncate">{name ?? <span className="text-subtle-foreground">bez nazwy i opisu</span>}</div>
        {address ? <div className="type-caption truncate text-muted-foreground">{address}</div> : null}
        {!r.is_valid || r.issues.length ? (
          <div className="mt-1 flex items-start gap-1.5">
            <Badge variant={r.is_valid ? "caution" : "destructive"} className="shrink-0">
              {r.is_valid ? "Uwagi" : "Odrzucony"}
            </Badge>
            <span className="type-micro text-muted-foreground">{r.issues.map(issueText).join("; ")}</span>
          </div>
        ) : null}
        {r.removed_at ? (
          <div className="type-micro mt-1 text-muted-foreground">Usunięty ze źródła {formatRelative(r.removed_at)}</div>
        ) : null}
      </TableCell>
      <TableCell className="font-mono text-xs tabular-nums max-md:hidden">
        {r.lat !== null && r.lon !== null ? `${r.lat.toFixed(5)}, ${r.lon.toFixed(5)}` : <span className="text-subtle-foreground">brak</span>}
      </TableCell>
      <TableCell>
        {r.device_id ? (
          <Link
            href={`/devices/${encodeURIComponent(r.device_id)}`}
            className="font-mono text-xs text-foreground underline decoration-border underline-offset-2 hover:decoration-foreground"
          >
            {r.device_id}
          </Link>
        ) : (
          <span className="type-caption text-subtle-foreground">nie trafił do rejestru</span>
        )}
      </TableCell>
      <TableCell className="type-caption text-muted-foreground max-lg:hidden" title={formatDateTime(r.last_seen)}>
        {formatRelative(r.last_seen)}
      </TableCell>
    </TableRow>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="min-w-0">
      <p className="type-caption mb-1 font-medium text-muted-foreground">{title}</p>
      <CodeBlock value={value} className="p-2" />
    </div>
  );
}
