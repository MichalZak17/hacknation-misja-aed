"use client";

import { useState } from "react";
import { UploadIcon } from "lucide-react";
import { toast } from "sonner";

import { ExternalLink, Facts } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError, type Integration } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { deliveryLabel } from "@/lib/integrations";

import { EditSourceDetails } from "./edit-source-dialog";
import { SourceSwitches } from "./source-switches";

/** Where the data comes from and how it is synchronised: the facts an admin checks and the few things they change. */
export function SourceSettings({ integration: i, onSaved }: { integration: Integration; onSaved: () => void }) {
  return (
    <div className="grid grid-cols-1 gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <section aria-labelledby="src-about">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 id="src-about" className="type-h4">
            Opis źródła
          </h2>
          <EditSourceDetails key={i.slug + i.name + i.source_url} integration={i} onSaved={onSaved} />
        </div>
        <Facts
          items={[
            {
              label: "Wydawca",
              value:
                i.publisher && i.homepage_url ? (
                  <UrlLink href={i.homepage_url}>{i.publisher}</UrlLink>
                ) : (
                  i.publisher || (i.homepage_url ? <UrlLink href={i.homepage_url} /> : null)
                ),
            },
            { label: "Atrybucja w eksporcie", value: i.attribution },
            {
              label: "Adres danych",
              value: i.accepts_upload ? "Plik wgrywany przez administratora" : i.source_url ? <UrlLink href={i.source_url} /> : null,
              wide: true,
            },
            { label: "Sposób pobierania", value: deliveryLabel(i) },
            {
              label: "Pierwszy pełny import",
              value: i.historical_completed_at ? formatDateTime(i.historical_completed_at) : "jeszcze nie",
            },
          ]}
        />
      </section>

      <section aria-labelledby="src-sync" className="flex flex-col gap-6">
        <div>
          <h2 id="src-sync" className="type-h4 mb-3">
            Synchronizacja
          </h2>
          <SourceSwitches integration={i} onSaved={onSaved} />
          <p className="type-caption mt-2 text-muted-foreground">
            Częstotliwość jest zapisana w kodzie integracji. Wyłączone źródło zostaje w zbiorze z ostatnimi danymi.
          </p>
        </div>
        <div>
          <h2 className="type-h4 mb-1">Priorytet {i.priority}</h2>
          <p className="type-caption text-muted-foreground">
            Gdy to samo urządzenie opisuje kilka źródeł, każde pole bierze się z tego o wyższym priorytecie. Wartości odczytane przez AI z opisów zawsze przegrywają z danymi podanymi wprost.
          </p>
        </div>
      </section>
    </div>
  );
}

/** A one-line external link: long URLs are cut with an ellipsis (full address in the tooltip). */
function UrlLink({ href, children }: { href: string; children?: React.ReactNode }) {
  const shown = children ?? href.replace(/^https?:\/\//, "").replace(/\/$/, "");
  return (
    <span className="flex min-w-0" title={href}>
      <ExternalLink href={href} className="max-w-full min-w-0">
        <span className="min-w-0 truncate">{shown}</span>
      </ExternalLink>
    </span>
  );
}

/** An operator's CSV/XLSX in the reference schema. Uploading only stores it: the next sync reads it. */
export function OperatorUpload({ integration: i, onUploaded }: { integration: Integration; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const current = typeof i.config.uploaded_file === "string" ? i.config.uploaded_file : null;

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;
    const form = e.currentTarget;
    setBusy(true);
    try {
      await api.upload(i.slug, file);
      toast.success(`Wgrano „${file.name}”. Sprawdź go bez zapisu, zanim go zaimportujesz.`);
      setFile(null);
      form.reset();
      onUploaded();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="upload-title" className="mb-6 bg-card px-4 py-4 ring-1 ring-border">
      <h2 id="upload-title" className="type-h4">
        Plik od dysponenta
      </h2>
      <p className="type-caption mt-0.5 mb-3 text-muted-foreground">
        {current ? `Teraz w użyciu: ${current}. ` : "Nie wgrano jeszcze pliku. "}
        Plik CSV lub XLSX we wzorcowym zakresie danych.{" "}
        <a href="/api/export/schema.xlsx" download className="text-link underline-offset-2 hover:underline">
          Pobierz szablon XLSX
        </a>
      </p>
      <form onSubmit={submit} className="flex flex-wrap items-center gap-3">
        <Label htmlFor="upload-file" className="sr-only">
          Plik CSV lub XLSX
        </Label>
        <Input
          id="upload-file"
          type="file"
          accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="max-w-sm"
        />
        <Button type="submit" variant="outline" disabled={!file || busy}>
          {busy ? <Spinner data-icon="inline-start" /> : <UploadIcon data-icon="inline-start" />}
          Wgraj plik
        </Button>
      </form>
    </section>
  );
}
