"use client";

import { Fragment, useState } from "react";
import { ChevronRightIcon } from "lucide-react";

import { EmptyState, ErrorAlert, LoadingRows, Pager, RunStatusBadge } from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type SyncRun } from "@/lib/api";
import { CHANGE_OP_LABEL, formatDateTime, formatDuration, formatNumber, formatRelative, label } from "@/lib/format";
import { issueText, runName, TRIGGER_PHRASE } from "@/lib/integrations";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const LIMIT = 25;
const COUNTS = [
  ["fetched", "Pobrano"],
  ["created", "Nowe"],
  ["updated", "Zmienione"],
  ["removed", "Usunięte"],
  ["invalid", "Błędne"],
] as const;

/**
 * The source's runs, a page at a time, newest first. A page carries only the counts; the changed records and
 * validation problems of one run load when its row is opened.
 *
 * `version` changes when the source's latest run starts or finishes, which refreshes the page.
 */
export function RunHistory({ slug, version, interval }: { slug: string; version: string; interval?: number }) {
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<number | null>(null);
  const runs = useApi(`runs:${slug}:${offset}:${version}`, () => api.integrationRuns(slug, { limit: LIMIT, offset }), {
    interval,
  });

  if (runs.error && !runs.data) return <ErrorAlert error={runs.error} />;
  if (!runs.data) return <LoadingRows />;
  if (runs.data.count === 0)
    return (
      <EmptyState
        title="Jeszcze nic nie uruchomiono"
        description="Zacznij od „Sprawdź bez zapisu”, a jeśli wynik jest dobry, zaimportuj cały zbiór."
      />
    );

  return (
    <>
      <div className={cn(runs.loading && "opacity-60")}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Kiedy</TableHead>
              <TableHead>Rodzaj</TableHead>
              <TableHead>Wynik</TableHead>
              {COUNTS.map(([key, title]) => (
                <TableHead key={key} className={cn("text-right", key !== "fetched" && "max-md:hidden")}>
                  {title}
                </TableHead>
              ))}
              <TableHead className="text-right max-lg:hidden">Czas</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.data.items.map((r) => (
              <Fragment key={r.id}>
                <RunRow run={r} open={open === r.id} onToggle={() => setOpen(open === r.id ? null : r.id)} />
                {open === r.id ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={9} className="bg-canvas p-3 whitespace-normal">
                      <RunDetails id={r.id} />
                    </TableCell>
                  </TableRow>
                ) : null}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
      <Pager count={runs.data.count} limit={LIMIT} offset={offset} onChange={setOffset} />
    </>
  );
}

function RunRow({ run: r, open, onToggle }: { run: SyncRun; open: boolean; onToggle: () => void }) {
  const done = r.status === "success" || r.status === "failed";
  return (
    <TableRow className={cn(open && "bg-selected")}>
      <TableCell>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={`run-${r.id}`}
          onClick={onToggle}
          title={formatRelative(r.created_at)}
          className="inline-flex items-center gap-1 tabular-nums outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <ChevronRightIcon aria-hidden className={cn("size-3.5 text-muted-foreground", open && "rotate-90")} />
          {formatDateTime(r.created_at)}
        </button>
      </TableCell>
      <TableCell>
        {runName(r)}
        <div className="type-caption text-muted-foreground">{TRIGGER_PHRASE[r.trigger] ?? r.trigger}</div>
      </TableCell>
      <TableCell>
        <RunStatusBadge status={r.status} />
      </TableCell>
      {COUNTS.map(([key]) => (
        <TableCell
          key={key}
          className={cn(
            "text-right tabular-nums",
            key !== "fetched" && "max-md:hidden",
            (!done || r[key] === 0) && "text-subtle-foreground",
            key === "invalid" && r.invalid > 0 && "text-caution-subtle-foreground dark:text-caution",
          )}
        >
          {done ? formatNumber(r[key]) : "–"}
        </TableCell>
      ))}
      <TableCell className="text-right text-muted-foreground tabular-nums max-lg:hidden">
        {r.duration_ms !== null ? formatDuration(r.duration_ms) : "–"}
      </TableCell>
    </TableRow>
  );
}

/** One run's error, changed records and validation problems, fetched when its row opens. */
function RunDetails({ id }: { id: number }) {
  const run = useApi(`run:${id}`, () => api.run(id));
  if (run.error) return <ErrorAlert error={run.error} />;
  const r = run.data;
  if (!r) return <LoadingRows rows={2} />;
  const changes = r.details?.changes ?? [];
  const issues = r.details?.issues ?? [];

  return (
    <div id={`run-${id}`}>
      {r.error ? (
        <pre className="type-code mb-3 overflow-auto bg-negative-subtle p-2 whitespace-pre-wrap text-negative-subtle-foreground">
          {r.error}
        </pre>
      ) : null}
      {!r.error && changes.length === 0 && issues.length === 0 ? (
        <p className="type-caption text-muted-foreground">Żaden rekord się nie zmienił i wszystkie przeszły walidację.</p>
      ) : null}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {changes.length > 0 ? (
          <div className="min-w-0">
            <h3 className="type-h4 mb-1">
              Zmienione rekordy ({changes.length}
              {r.details.truncated ? "+" : ""})
            </h3>
            <ul className="max-h-64 overflow-auto">
              {changes.map((c, idx) => (
                <li key={`${c.source_record_id}-${idx}`} className="type-caption flex flex-wrap items-center gap-2 border-b border-border py-1">
                  <Badge variant={c.op === "remove" ? "destructive" : c.op === "create" ? "positive" : "info"}>
                    {label(CHANGE_OP_LABEL, c.op)}
                  </Badge>
                  <span className="font-mono">{c.source_record_id}</span>
                  {c.fields?.length ? <span className="text-muted-foreground">{c.fields.join(", ")}</span> : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {issues.length > 0 ? (
          <div className="min-w-0">
            <h3 className="type-h4 mb-1">Nie przeszły walidacji ({issues.length})</h3>
            <ul className="max-h-64 overflow-auto">
              {issues.map((it, idx) => (
                <li key={`${it.source_record_id}-${idx}`} className="type-caption border-b border-border py-1">
                  <span className="font-mono">{it.source_record_id}</span>{" "}
                  <span className="text-muted-foreground">{it.issues.map(issueText).join("; ")}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      {r.details?.truncated ? (
        <p className="type-micro mt-2 text-subtle-foreground">Lista skrócona. Pełny wynik jest w logu uruchomienia.</p>
      ) : null}
    </div>
  );
}
