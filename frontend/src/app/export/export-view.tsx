"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRightIcon, CheckIcon, CopyIcon, DownloadIcon } from "lucide-react";
import { toast } from "sonner";

import { MetaLabel, SectionHeading } from "@/components/brand";
import { ErrorAlert, LoadingRows, Section } from "@/components/app/ui";
import { KeyFact } from "@/components/docs/live";
import { Button } from "@/components/ui/button";
import { api, type ExportResource } from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import { DOCS_ENABLED } from "@/lib/features";
import { formatBytes, formatDate, formatDateTime, formatNumber } from "@/lib/format";
import { useApi } from "@/lib/use-api";

import { CoverageMatrix } from "./_components/coverage-matrix";

/** Exports are proxied by Next on the same origin as this page, so that is the address to register. */
function absolute(path: string) {
  return typeof window === "undefined" ? path : new URL(path, window.location.origin).toString();
}

/** Where the explanations went: the documentation, which needs no login either. */
const DOCS = [
  { href: "/docs/publikacja", title: "Jak opublikować na dane.gov.pl", hint: "Źródło XML albo ręcznie, krok po kroku" },
  { href: "/docs/metadane-zbioru", title: "Metadane zbioru", hint: "Tytuł, opis, licencja, kategorie" },
  { href: "/docs/slownik-danych", title: "Słownik danych", hint: "Każde pole rekordu, z przykładem" },
  { href: "/docs/zrodla-danych", title: "Źródła danych", hint: "Skąd pochodzą rekordy i na jakiej licencji" },
] as const;

/** Public page, kept to what you come here to do: take the files. Everything that explains them is in /docs (dev only). */
export function ExportView() {
  const dataset = useApi("dataset", api.dataset);
  const d = dataset.data;

  return (
    <>
      <div className="mb-8">
        <MetaLabel prompt>Otwarte dane · dane.gov.pl</MetaLabel>
        <SectionHeading as="h1" className="mt-2">
          Defibrylatory AED w Polsce
        </SectionHeading>
        <p className="type-lead mt-3 max-w-3xl text-muted-foreground">
          Jeden ogólnopolski zbiór: gdzie jest AED, czy jest dostępne i czy jest gotowe do użycia. Dane z wielu źródeł
          scalone w jeden rekord na urządzenie, w formatach odczytywalnych maszynowo.
        </p>
      </div>

      {dataset.error ? <ErrorAlert error={dataset.error} /> : null}

      <dl className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KeyFact label="Urządzenia" value={d ? formatNumber(d.metadata.records) : "…"} />
        <KeyFact label="Pól w rekordzie" value={d ? formatNumber(d.metadata.fields) : "…"} />
        <KeyFact label="Stan danych na" value={d ? formatDate(d.dataset.data_date) : "…"} />
        <KeyFact label="Aktualizacja" value={d ? d.dataset.update_frequency_label : "…"} />
      </dl>

      <div className="flex flex-col gap-6">
        <Section title="Zasoby do pobrania">
          <p className="type-body mb-4 max-w-3xl text-muted-foreground">
            Adresy są stałe: każda synchronizacja źródeł podmienia plik pod tym samym linkiem. Na dane.gov.pl zasób dodaje
            się jako link, więc skopiuj adres przy wybranym formacie.
          </p>
          {!d ? (
            <LoadingRows rows={3} />
          ) : (
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              {d.resources.map((r) => (
                <li key={r.path}>
                  <ResourceCard resource={r} />
                </li>
              ))}
            </ul>
          )}
          <p className="type-caption mt-4 text-muted-foreground">
            Wzorcowy zakres danych (szablon dla dysponentów) jest też w CSV:{" "}
            <a href="/api/export/schema-template.csv" download className="text-link underline-offset-2 hover:underline">
              pobierz szablon CSV
            </a>
            .
          </p>
          {d ? (
            <p className="type-micro mt-4 text-subtle-foreground">
              Wersja danych {d.metadata.data_version} · wygenerowano {formatDateTime(d.metadata.generated_at)}
            </p>
          ) : null}
        </Section>

        <CoverageMatrix />

        {DOCS_ENABLED ? (
          <Section title="Dokumentacja zbioru">
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {DOCS.map((doc) => (
                <li key={doc.href}>
                  <Link
                    href={doc.href}
                    className="group flex h-full items-start justify-between gap-3 bg-background p-4 ring-1 ring-border outline-none hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    <span className="min-w-0">
                      <span className="type-body block font-semibold text-foreground">{doc.title}</span>
                      <span className="type-caption mt-1 block text-muted-foreground">{doc.hint}</span>
                    </span>
                    <ArrowRightIcon aria-hidden className="mt-0.5 size-4 shrink-0 text-subtle-foreground group-hover:text-hn-crimson" />
                  </Link>
                </li>
              ))}
            </ul>
          </Section>
        ) : null}
      </div>
    </>
  );
}

function OpennessStars({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span aria-hidden className="tracking-[0.1em] text-hn-crimson">
        {"★".repeat(score)}
        <span className="text-subtle-foreground">{"☆".repeat(5 - score)}</span>
      </span>
      <span className="sr-only">Otwartość: {score} z 5 gwiazdek</span>
    </span>
  );
}

function ResourceCard({ resource: r }: { resource: ExportResource }) {
  const link = absolute(r.path);
  const isApi = r.media_type === "api";
  const label = isApi ? "api" : r.format;
  const id = `res-${r.path.replace(/[^a-z0-9]+/gi, "-")}`;
  return (
    <article
      aria-labelledby={id}
      className="flex h-full flex-col gap-3 bg-background p-4 ring-1 ring-border"
    >
      <div className="flex items-start justify-between gap-2">
        <h3
          id={id}
          className="font-display text-[2rem] leading-none tracking-[0.02em] text-hn-heading uppercase"
        >
          {label}
        </h3>
        {r.openness_score ? <OpennessStars score={r.openness_score} /> : null}
      </div>
      <p className="type-body font-medium text-foreground">{r.title}</p>
      <p className="type-body text-muted-foreground">{r.description}</p>
      <p className="type-caption text-subtle-foreground">
        {isApi ? "API na żywo" : formatBytes(r.file_size)} · {r.content_type} · stan na{" "}
        {formatDate(r.data_date)}
      </p>
      <div className="mt-auto flex flex-col gap-2">
        <Button asChild variant="default" size="sm">
          {isApi ? (
            <a href="/api/v1/docs">
              Dokumentacja API
              <span className="sr-only"> — {r.title}</span>
            </a>
          ) : (
            <a href={r.path} download>
              <DownloadIcon data-icon="inline-start" aria-hidden />
              Pobierz {r.format.toUpperCase()}
              <span className="sr-only"> — {r.title}</span>
            </a>
          )}
        </Button>
        <CopyLink
          value={link}
          label={`Kopiuj link do zasobu ${label.toUpperCase()}`}
        />
      </div>
    </article>
  );
}

function CopyLink({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    if (await copyText(value)) {
      setCopied(true);
      toast.success("Skopiowano link do schowka.");
      window.setTimeout(() => setCopied(false), 2000);
    } else {
      toast.error("Nie udało się skopiować — zaznacz adres ręcznie.");
    }
  }
  return (
    <div className="flex items-stretch ring-1 ring-border">
      <code
        className="type-code min-w-0 flex-1 truncate bg-muted px-2 py-1.5"
        title={value}
      >
        {value}
      </code>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={label}
        onClick={() => void copy()}
      >
        {copied ? <CheckIcon aria-hidden /> : <CopyIcon aria-hidden />}
      </Button>
    </div>
  );
}
