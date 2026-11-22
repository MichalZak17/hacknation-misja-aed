"use client";

import Link from "next/link";
import { useState } from "react";
import { MailIcon, MapPinIcon, SaveIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorAlert, LoadingRows, PageHeader, Pager } from "@/components/app/ui";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  REPORT_STATUS_LABEL,
  reportsApi,
  type Report,
  type ReportKind,
  type ReportStatus,
} from "@/lib/api";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useApi } from "@/lib/use-api";

const LIMIT = 20;
type Filter = ReportStatus | "all";
const STATUSES: ReportStatus[] = ["new", "in_review", "resolved", "rejected"];

const STATUS_VARIANT = {
  new: "info",
  in_review: "caution",
  resolved: "positive",
  rejected: "secondary",
} as const;

/** A broken or locked AED decides whether someone finds a working one: those go first in a reviewer's eye. */
const URGENT: ReportKind[] = ["not_working", "locked"];

export default function ReportsPage() {
  const [filter, setFilter] = useState<Filter>("new");
  const [offset, setOffset] = useState(0);
  const reports = useApi(`reports:${filter}:${offset}`, () =>
    reportsApi.list({ status: filter === "all" ? "" : filter, limit: LIMIT, offset }),
  );
  const counts = reports.data?.counts;
  const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : undefined;
  const withCount = (label: string, n: number | undefined) => (n === undefined ? label : `${label} (${n})`);

  return (
    <>
      <PageHeader
        title="Zgłoszenia"
        description={
          <>
            Od mieszkańców i dysponentów, z publicznego formularza{" "}
            <Link href="/zglos" className="text-link hover:text-link-hover hover:underline">
              /zglos
            </Link>
            . Nie zmieniają zbioru same: potwierdzoną poprawkę wprowadź przez źródło (plik dysponenta, zdarzenie
            serwisowe).
          </>
        }
        actions={
          <SegmentedControl<Filter>
            label="Status zgłoszeń"
            value={filter}
            onValueChange={(v) => {
              setFilter(v);
              setOffset(0);
            }}
            options={[
              ...STATUSES.map((s) => ({ value: s, label: withCount(REPORT_STATUS_LABEL[s], counts?.[s]) })),
              { value: "all" as const, label: withCount("Wszystkie", total) },
            ]}
          />
        }
      />
      {reports.error ? <ErrorAlert error={reports.error} /> : null}
      {!reports.data ? (
        <LoadingRows rows={6} />
      ) : reports.data.items.length === 0 ? (
        <EmptyState
          title={filter === "new" ? "Brak nowych zgłoszeń" : "Brak zgłoszeń"}
          description={filter === "new" ? "Wszystkie zgłoszenia mają już status." : undefined}
        />
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {reports.data.items.map((r) => (
              <li key={r.id}>
                <ReportCard report={r} onChange={() => void reports.reload()} />
              </li>
            ))}
          </ul>
          <Pager count={reports.data.count} limit={LIMIT} offset={offset} onChange={setOffset} />
        </>
      )}
    </>
  );
}

function osmLink(lat: number, lon: number) {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=19/${lat}/${lon}`;
}

function ReportCard({ report: r, onChange }: { report: Report; onChange: () => void }) {
  const [status, setStatus] = useState<ReportStatus>(r.status);
  const [note, setNote] = useState(r.admin_note);
  const [busy, setBusy] = useState(false);
  const dirty = status !== r.status || note.trim() !== r.admin_note;
  const headingId = `report-${r.id}`;

  async function save() {
    setBusy(true);
    try {
      await reportsApi.update(r.id, { status, admin_note: note });
      toast.success(`Zapisano zgłoszenie #${r.id}.`);
      onChange();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    try {
      await reportsApi.remove(r.id);
      toast.success(`Usunięto zgłoszenie #${r.id}.`);
      onChange();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    }
  }

  const d = r.device;
  return (
    <article aria-labelledby={headingId} className="bg-card ring-1 ring-border">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-border px-4 py-2">
        <h2 id={headingId} className="type-h4 text-hn-heading">
          <span className="type-label mr-2 text-subtle-foreground">#{r.id}</span>
          {r.kind_label}
        </h2>
        {URGENT.includes(r.kind) && r.status !== "resolved" && r.status !== "rejected" ? (
          <Badge variant="destructive">Pilne</Badge>
        ) : null}
        <Badge variant={STATUS_VARIANT[r.status]}>{REPORT_STATUS_LABEL[r.status]}</Badge>
        <time dateTime={r.created_at} title={formatDateTime(r.created_at)} className="type-caption ml-auto text-subtle-foreground">
          {formatRelative(r.created_at)}
        </time>
      </header>

      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0">
          <p className="type-body whitespace-pre-wrap break-words text-foreground">{r.description}</p>
          <dl className="type-caption mt-3 grid gap-x-4 gap-y-1 text-muted-foreground sm:grid-cols-[auto_1fr]">
            <dt className="font-semibold text-subtle-foreground">AED</dt>
            <dd className="min-w-0 break-words">
              {d ? (
                <>
                  <Link
                    href={`/devices/${encodeURIComponent(d.id)}`}
                    className="font-mono text-link hover:text-link-hover hover:underline"
                  >
                    {d.id}
                  </Link>
                  {d.name || d.address ? (
                    <span> · {[d.name, d.address, d.city].filter(Boolean).join(", ")}</span>
                  ) : null}
                </>
              ) : (
                "nie wskazano"
              )}
            </dd>
            <dt className="font-semibold text-subtle-foreground">Miejsce</dt>
            <dd>
              {r.lat !== null && r.lon !== null ? (
                <a
                  href={osmLink(r.lat, r.lon)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-link hover:text-link-hover hover:underline"
                >
                  <MapPinIcon aria-hidden className="size-3.5" />
                  {r.lat.toFixed(5)}, {r.lon.toFixed(5)}
                  <span className="sr-only"> (OpenStreetMap, nowe okno)</span>
                </a>
              ) : (
                "nie podano"
              )}
            </dd>
            <dt className="font-semibold text-subtle-foreground">Kontakt</dt>
            <dd className="min-w-0 break-words">
              {r.contact_email ? (
                <a
                  href={`mailto:${r.contact_email}?subject=${encodeURIComponent(`Zgłoszenie AED #${r.id}`)}`}
                  className="inline-flex items-center gap-1 text-link hover:text-link-hover hover:underline"
                >
                  <MailIcon aria-hidden className="size-3.5" />
                  {r.contact_email}
                </a>
              ) : (
                "brak (zgłoszenie anonimowe)"
              )}
            </dd>
          </dl>
        </div>

        <div className="flex flex-col gap-3 border-t border-border pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`status-${r.id}`} className="type-caption font-semibold text-foreground">
              Status
            </label>
            <NativeSelect
              id={`status-${r.id}`}
              value={status}
              onChange={(e) => setStatus(e.target.value as ReportStatus)}
              className="w-full"
            >
              {STATUSES.map((s) => (
                <NativeSelectOption key={s} value={s}>
                  {REPORT_STATUS_LABEL[s]}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`note-${r.id}`} className="type-caption font-semibold text-foreground">
              Notatka (widzą tylko administratorzy)
            </label>
            <Textarea
              id={`note-${r.id}`}
              value={note}
              maxLength={2000}
              rows={2}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Trash2Icon data-icon="inline-start" aria-hidden />
                  Usuń<span className="sr-only"> zgłoszenie #{r.id}</span>
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Usunąć zgłoszenie #{r.id}?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Na przykład spam albo test. Tego nie można cofnąć; zwykłe zgłoszenia lepiej oznaczyć jako odrzucone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Anuluj</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" onClick={() => void remove()}>
                    Usuń
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Button size="sm" disabled={!dirty || busy} onClick={() => void save()}>
              <SaveIcon data-icon="inline-start" aria-hidden />
              Zapisz<span className="sr-only"> zgłoszenie #{r.id}</span>
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
