"use client";

import Link from "next/link";
import { useState } from "react";
import { RefreshCwIcon } from "lucide-react";
import { toast } from "sonner";

import { ErrorAlert, LoadingRows, PageHeader } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError, type Integration } from "@/lib/api";
import { formatDateTime, formatNumber, formatRelative } from "@/lib/format";
import { deliveryLabel, health, pollInterval } from "@/lib/integrations";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

import { HealthBadge, RunStrip } from "./_components/health";
import { NewSourceDialog } from "./_components/new-source-dialog";

/** Sources by merge priority: when two sources describe the same AED, each field comes from the one higher up. */
export default function IntegrationsPage() {
  const [pollMs, setPollMs] = useState<number | undefined>(undefined);
  const list = useApi("integrations", api.integrations, { interval: pollMs });
  const next = pollInterval(list.data);
  if (next !== pollMs) setPollMs(next);
  const reload = () => void list.reload();

  return (
    <>
      <PageHeader
        title="Integracje"
        actions={<NewSourceDialog onCreated={reload} />}
      />
      {list.error ? <ErrorAlert error={list.error} /> : null}
      {!list.data ? (
        <LoadingRows rows={7} />
      ) : (
        <div className="bg-card ring-1 ring-border">
          <div
            aria-hidden
            className="type-caption hidden grid-cols-[4.5rem_minmax(0,1fr)_7rem_7.5rem_11rem_3rem] items-end gap-x-4 border-b border-border px-4 py-2 text-subtle-foreground lg:grid"
          >
            <span>Priorytet</span>
            <span>Źródło</span>
            <span className="text-right">Urządzenia</span>
            <span>Uruchomienia</span>
            <span>Stan</span>
            <span />
          </div>
          {list.data.length === 0 ? (
            <p className="type-body px-4 py-6 text-muted-foreground">
              Nie ma jeszcze żadnych źródeł. Dodaj dysponenta, a potem wgraj jego plik CSV lub XLSX.
            </p>
          ) : (
            <ul>
              {list.data.map((i) => (
                <li key={i.slug} className="border-t border-border first:border-t-0">
                  <SourceRow integration={i} onChange={reload} />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}

function SourceRow({ integration: i, onChange }: { integration: Integration; onChange: () => void }) {
  const h = health(i);
  return (
    <div
      className={cn(
        "group relative grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-x-4 gap-y-2 px-4 py-3 transition-colors duration-150 hover:bg-accent lg:grid-cols-[4.5rem_minmax(0,1fr)_7rem_7.5rem_11rem_3rem]",
        !i.enabled && "text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "type-h4 row-span-3 self-start tabular-nums lg:row-span-1 lg:self-center",
          i.enabled ? "text-foreground" : "text-disabled-foreground",
        )}
        title="Priorytet przy scalaniu"
      >
        <span className="sr-only">Priorytet </span>
        {i.priority}
      </span>

      <div className="min-w-0">
        <Link
          href={`/integrations/${i.slug}`}
          className="type-h4 block truncate text-foreground outline-none after:absolute after:inset-0 group-hover:underline focus-visible:after:outline-2 focus-visible:after:-outline-offset-2 focus-visible:after:outline-ring"
        >
          {i.name}
        </Link>
        <p className="type-caption truncate text-muted-foreground">
          {[i.publisher, deliveryLabel(i)].filter(Boolean).join(". ")}
        </p>
      </div>

      <p className="type-body tabular-nums lg:text-right">
        <span className="font-semibold">{formatNumber(i.devices)}</span>
        <span className="text-muted-foreground lg:sr-only"> urządzeń</span>
      </p>

      <RunStrip runs={i.recent_runs} className="col-start-2 lg:col-start-auto" />

      <div className="col-start-2 min-w-0 lg:col-start-auto">
        <HealthBadge tone={h.tone} label={h.label} />
        <p className="type-micro mt-0.5 text-subtle-foreground" title={formatDateTime(i.last_success_at)}>
          {i.last_success_at ? `odświeżone ${formatRelative(i.last_success_at)}` : "jeszcze bez danych"}
        </p>
      </div>

      <div className="col-start-2 lg:col-start-auto lg:justify-self-end">
        <QuickSync integration={i} onChange={onChange} />
      </div>
    </div>
  );
}

/** A regular sync straight from the list, once the source has data. Everything else is on the source's page. */
function QuickSync({ integration: i, onChange }: { integration: Integration; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  if (!i.enabled || !i.historical_completed_at) return null;

  async function sync() {
    setBusy(true);
    try {
      await api.sync(i.slug, { kind: "periodic", dry_run: false, force: false });
      toast.success(`Synchronizacja „${i.name}” w kolejce.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setBusy(false);
      onChange();
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className="relative z-10"
      disabled={busy || i.running}
      onClick={() => void sync()}
      aria-label={`Synchronizuj teraz: ${i.name}`}
      title="Synchronizuj teraz"
    >
      {busy || i.running ? <Spinner /> : <RefreshCwIcon />}
    </Button>
  );
}
