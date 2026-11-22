"use client";

import { useState } from "react";
import { DownloadIcon } from "lucide-react";

import { ErrorAlert, ExternalLink, Facts, LoadingRows } from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type SchemaField } from "@/lib/api";
import { formatBytes, formatDate, formatDateTime, formatNumber } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

/**
 * Parts of the documentation that must never go stale: they read the same API as the published files, so the
 * metadata, the data dictionary and the source list on /docs always match what dane.gov.pl imports. Used from MDX.
 */

const LEVELS = [
  { value: 1, label: "Podstawowy", hint: "wymagany" },
  { value: 2, label: "Rozszerzony", hint: "dostępność i lokalizacja w obiekcie" },
  { value: 3, label: "Pełny", hint: "dane serwisowe dysponenta" },
] as const;

export function KeyFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card p-4 ring-1 ring-border">
      <dt className="type-label text-subtle-foreground">{label}</dt>
      <dd className="type-h2 mt-1 text-hn-heading tabular-nums">{value}</dd>
    </div>
  );
}

/** The four numbers that describe the dataset today. */
export function DatasetFacts() {
  const dataset = useApi("dataset", api.dataset);
  const d = dataset.data;
  return (
    <>
      {dataset.error ? <ErrorAlert error={dataset.error} /> : null}
      <dl className="not-prose my-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KeyFact label="Urządzenia" value={d ? formatNumber(d.metadata.records) : "…"} />
        <KeyFact label="Pól w rekordzie" value={d ? formatNumber(d.metadata.fields) : "…"} />
        <KeyFact label="Stan danych na" value={d ? formatDate(d.dataset.data_date) : "…"} />
        <KeyFact label="Aktualizacja" value={d ? d.dataset.update_frequency_label : "…"} />
      </dl>
    </>
  );
}

/** What is typed into dane.gov.pl for this dataset: title, description, categories, licence and so on. */
export function DatasetMetadata() {
  const dataset = useApi("dataset", api.dataset);
  const d = dataset.data;
  if (dataset.error) return <ErrorAlert error={dataset.error} />;
  if (!d) return <LoadingRows rows={4} />;
  return (
    <div className="my-6 bg-card p-4 ring-1 ring-border">
      <Facts
        items={[
          { label: "Tytuł", value: d.dataset.title },
          {
            label: "Częstotliwość aktualizacji",
            value: `${d.dataset.update_frequency_label} (${d.dataset.update_frequency})`,
          },
          { label: "Opis", wide: true, value: <span className="whitespace-pre-line">{stripHtml(d.dataset.notes)}</span> },
          {
            label: "Kategorie",
            value: (
              <span className="flex flex-wrap gap-1">
                {d.dataset.categories.map((c) => (
                  <Badge key={c.code} variant="outline">
                    {c.title} ({c.code})
                  </Badge>
                ))}
              </span>
            ),
          },
          {
            label: "Słowa kluczowe",
            value: (
              <span className="flex flex-wrap gap-1">
                {d.dataset.keywords.map((k) => (
                  <Badge key={k} variant="secondary">
                    {k}
                  </Badge>
                ))}
              </span>
            ),
          },
          {
            label: "Zasięg i język",
            value: `${d.dataset.regions.map((r) => r.name).join(", ")} · ${d.dataset.language}`,
          },
          {
            label: "Licencja i atrybucja",
            value: (
              <>
                <ExternalLink href={d.dataset.license_url}>{d.dataset.license_name}</ExternalLink>
                <span className="mt-1 block text-muted-foreground">{d.dataset.license_condition_custom_description}</span>
              </>
            ),
          },
          {
            label: "Dane osobowe",
            value: "nie zawiera (wyłącznie kontakty instytucjonalne)",
          },
          {
            label: "Wykaz chronionych danych (DGA)",
            wide: true,
            value: (
              <>
                {d.dga.resources.map((r) => (
                  <a key={r.path} href={r.path} download className="underline underline-offset-2">
                    {r.title} ({r.format.toUpperCase()}
                    {r.file_size ? `, ${formatBytes(r.file_size)}` : ""})
                  </a>
                ))}
                <span className="mt-1 block text-muted-foreground">
                  Osobny zbiór w harvester.xml. Portal dane.gov.pl co noc przenosi go do zbiorczego wykazu
                  chronionych danych; dostęp do wymienionych danych jest możliwy na wniosek.
                </span>
              </>
            ),
          },
        ]}
      />
      <p className="type-micro mt-4 text-subtle-foreground">
        Wersja danych {d.metadata.data_version} · wygenerowano {formatDateTime(d.metadata.generated_at)}
      </p>
    </div>
  );
}

/** The data dictionary as files: the XLSX and the TXT. */
export function DictionaryDownloads() {
  const dataset = useApi("dataset", api.dataset);
  const d = dataset.data;
  if (!d) return null;
  const files = [
    ...d.resources.filter((r) => r.format === "xlsx"),
    ...d.supplements.filter((r) => r.path.endsWith("/schema.txt")),
  ];
  return (
    <p className="not-prose my-4 flex flex-wrap gap-2">
      {files.map((r) => (
        <Button key={r.path} asChild variant="outline" size="sm">
          <a href={r.path} download>
            <DownloadIcon data-icon="inline-start" aria-hidden />
            Słownik {r.format.toUpperCase()} ({formatBytes(r.file_size)})
          </a>
        </Button>
      ))}
    </p>
  );
}

/** Every field of the record, filterable by scope level. */
export function SchemaTable() {
  const schema = useApi("schema", api.schema);
  if (schema.error) return <ErrorAlert error={schema.error} />;
  if (!schema.data) return <LoadingRows />;
  return <Fields fields={schema.data} />;
}

function Fields({ fields }: { fields: SchemaField[] }) {
  const [level, setLevel] = useState<number | null>(null);
  const shown = level === null ? fields : fields.filter((f) => f.level === level);
  return (
    <div className="not-prose my-6">
      <div role="group" aria-label="Poziom zakresu danych" className="mb-4 flex flex-wrap gap-2">
        <FilterButton active={level === null} onClick={() => setLevel(null)}>
          Wszystkie ({fields.length})
        </FilterButton>
        {LEVELS.map((l) => (
          <FilterButton key={l.value} active={level === l.value} onClick={() => setLevel(l.value)} title={l.hint}>
            {l.value} · {l.label} ({fields.filter((f) => f.level === l.value).length})
          </FilterButton>
        ))}
      </div>
      <Table>
        <caption className="sr-only">Pola wzorcowego zakresu danych AED</caption>
        <TableHeader>
          <TableRow>
            <TableHead>Pole</TableHead>
            <TableHead>Nazwa</TableHead>
            <TableHead>Typ</TableHead>
            <TableHead>Poziom</TableHead>
            <TableHead>Przykład</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.map((f) => (
            <TableRow key={f.field}>
              <TableCell>
                <code className="type-code">{f.field}</code>
              </TableCell>
              <TableCell className="min-w-48 whitespace-normal">
                {f.label}
                {f.note ? <span className="type-micro block text-subtle-foreground">{f.note}</span> : null}
              </TableCell>
              <TableCell className="whitespace-normal">{f.type}</TableCell>
              <TableCell>{f.level}</TableCell>
              <TableCell>
                <code className="type-code">{f.example}</code>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  title,
  children,
}: {
  active: boolean;
  onClick: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Button
      type="button"
      variant="filter"
      size="sm"
      aria-pressed={active}
      data-active={active}
      title={title}
      onClick={onClick}
      className={cn(active && "bg-secondary-hover")}
    >
      {children}
    </Button>
  );
}

/** Publishers and licences of the sources merged into the dataset. */
export function SourcesTable() {
  const dataset = useApi("dataset", api.dataset);
  const d = dataset.data;
  if (dataset.error) return <ErrorAlert error={dataset.error} />;
  if (!d) return <LoadingRows rows={4} />;
  return (
    <div className="not-prose my-6">
      <Table>
        <caption className="sr-only">Źródła danych scalone w zbiorze</caption>
        <TableHeader>
          <TableRow>
            <TableHead>Źródło</TableHead>
            <TableHead>Wydawca</TableHead>
            <TableHead>Licencja</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {d.sources.map((s) => (
            <TableRow key={s.slug}>
              <TableCell className="whitespace-normal">
                {s.homepage_url ? <ExternalLink href={s.homepage_url}>{s.name}</ExternalLink> : s.name}
              </TableCell>
              <TableCell className="whitespace-normal">{s.publisher || "—"}</TableCell>
              <TableCell className="whitespace-normal">
                {s.license_url ? <ExternalLink href={s.license_url}>{s.license || "licencja"}</ExternalLink> : s.license || "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** The dataset description is HTML for the portal; here it is shown as plain paragraphs. */
function stripHtml(html: string) {
  return html
    .replace(/<\/p>\s*<p>/g, "\n\n")
    .replace(/<[^>]+>/g, "")
    .trim();
}
