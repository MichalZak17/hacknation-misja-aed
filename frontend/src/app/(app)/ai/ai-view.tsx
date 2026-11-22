"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { CpuIcon, RefreshCwIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorAlert, LoadingRows, PageHeader } from "@/components/app/ui";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError, type EnrichmentStatus } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { plural } from "@/lib/integrations";
import { useApi } from "@/lib/use-api";

import { LiveRunView } from "./live-run";

/** Measured on the shared vLLM: about 3 answers a second with 16 parallel requests (docs/llm-extraction). */
const ANSWERS_PER_SECOND_AT_16 = 3;

function estimate(texts: number, concurrency: number) {
  const seconds = texts / (ANSWERS_PER_SECOND_AT_16 * Math.max(concurrency, 1) / 16);
  if (seconds < 90) return `około ${Math.max(10, Math.round(seconds / 10) * 10)} s`;
  const minutes = Math.round(seconds / 60);
  return minutes < 90 ? `około ${minutes} min` : `około ${Math.round(minutes / 6) / 10} h`;
}

/**
 * The AI classification step made visible: pick a source, ask the model to read its free-text descriptions again, and
 * watch every answer arrive — the text it read, the fields it returned, and how the totals build up.
 */
export function AiView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const status = useApi("enrichment", api.enrichment, { interval: 30_000 });
  // Short polling even when idle, so a run started elsewhere (schedule, integrations page) shows up within seconds
  const list = useApi("integrations", api.integrations, { interval: 5_000 });

  const sources = status.data?.sources ?? [];
  const slug = params.get("source") ?? sources.find((s) => s.with_text > 0)?.slug ?? sources[0]?.slug ?? null;
  const integration = list.data?.find((i) => i.slug === slug);
  const source = sources.find((s) => s.slug === slug);
  const paramRun = Number(params.get("run")) || null;
  // A run started from elsewhere (schedule, integrations page) takes over the view while it works
  const activeRun = integration?.running ? integration.last_run?.id ?? null : null;
  const runId = activeRun ?? paramRun ?? integration?.last_run?.id ?? null;

  const go = (s: string | null, run?: number) => {
    const q = new URLSearchParams();
    if (s) q.set("source", s);
    if (run) q.set("run", String(run));
    router.replace(`${pathname}?${q}`, { scroll: false });
  };

  return (
    <>
      <PageHeader
        title="Klasyfikacja AI"
        description="Model językowy czyta opisy ze źródeł (gdzie wisi defibrylator, jak się do niego dostać, w jakich godzinach) i zamienia je na pola zbioru. Tu widać to na żywo: tekst, który przeczytał, i to, co z niego odczytał."
        meta={status.data ? <ModelChip status={status.data} /> : null}
      />
      {status.error ? <ErrorAlert error={status.error} /> : null}
      {list.error ? <ErrorAlert error={list.error} /> : null}
      {!status.data || !list.data ? (
        <LoadingRows rows={6} />
      ) : sources.length === 0 ? (
        <EmptyState title="Brak źródeł" description="Dodaj i zsynchronizuj źródło, aby było co klasyfikować." />
      ) : (
        <>
          <Controls
            status={status.data}
            slug={slug}
            withText={source?.with_text ?? 0}
            running={Boolean(integration?.running)}
            enabled={Boolean(integration?.enabled)}
            onSource={(s) => go(s)}
            onQueued={(run) => {
              go(slug, run);
              void list.reload();
            }}
          />
          {runId !== null && slug ? (
            <LiveRunView
              key={runId}
              runId={runId}
              slug={slug}
              concurrency={status.data.concurrency}
              onFinished={() => {
                void list.reload();
                void status.reload();
              }}
            />
          ) : (
            <EmptyState
              title="To źródło nie było jeszcze synchronizowane"
              description="Uruchom klasyfikację, aby zobaczyć, jak model czyta jego opisy."
            />
          )}
          {slug ? (
            <p className="type-caption mt-6 text-subtle-foreground">
              Odczytane pola mają niższy priorytet niż dane podane przez źródło i są oznaczone w urządzeniu jako „AI, z
              opisu”. Historia przebiegów:{" "}
              <Link className="text-link hover:underline" href={`/integrations/${encodeURIComponent(slug)}`}>
                {integration?.name ?? slug}
              </Link>
              .
            </p>
          ) : null}
        </>
      )}
    </>
  );
}

function ModelChip({ status }: { status: EnrichmentStatus }) {
  if (!status.enabled) {
    return <Badge variant="caution">AI wyłączone (LLM_ENABLED)</Badge>;
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge variant={status.problem ? "caution" : "positive"} title={status.problem || undefined}>
        <CpuIcon aria-hidden />
        {status.problem ? "Model niedostępny" : "Model gotowy"}
      </Badge>
      <span className="type-caption text-muted-foreground">
        <span className="font-mono">{status.model}</span> · prompt <span className="font-mono">{status.prompt_version}</span> ·{" "}
        {status.concurrency} równoległych zapytań
      </span>
    </div>
  );
}

function Controls({
  status,
  slug,
  withText,
  running,
  enabled,
  onSource,
  onQueued,
}: {
  status: EnrichmentStatus;
  slug: string | null;
  withText: number;
  running: boolean;
  enabled: boolean;
  onSource: (slug: string) => void;
  onQueued: (run: number) => void;
}) {
  const [busy, setBusy] = useState<"reextract" | "sync" | null>(null);
  const [confirm, setConfirm] = useState(false);
  const blocked = !slug || !enabled || running || busy !== null;
  const llmReady = status.enabled && !status.problem;
  const name = status.sources.find((s) => s.slug === slug)?.name ?? slug;

  async function trigger(reextract: boolean) {
    if (!slug) return;
    setBusy(reextract ? "reextract" : "sync");
    try {
      const run = await api.sync(slug, { kind: "periodic", reextract });
      toast.success(reextract ? "Klasyfikacja w kolejce. Za chwilę zobaczysz pierwsze odpowiedzi." : "Synchronizacja w kolejce.");
      onQueued(run.id);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mb-6 flex flex-wrap items-end gap-3 bg-card p-4 ring-1 ring-border">
      <div className="flex min-w-64 flex-col gap-1.5">
        <Label htmlFor="ai-source">Źródło</Label>
        <NativeSelect id="ai-source" value={slug ?? ""} onChange={(e) => onSource(e.target.value)}>
          {status.sources.map((s) => (
            <NativeSelectOption key={s.slug} value={s.slug}>
              {s.name} — {formatNumber(s.with_text)} {plural(s.with_text, "opis", "opisy", "opisów")}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="cta" disabled={blocked || !llmReady || withText === 0} onClick={() => setConfirm(true)}>
          {busy === "reextract" ? <Spinner data-icon="inline-start" /> : <SparklesIcon data-icon="inline-start" />}
          Klasyfikuj ponownie
        </Button>
        <Button
          variant="outline"
          disabled={blocked}
          title="Zwykła synchronizacja: model czyta tylko opisy, które się zmieniły."
          onClick={() => void trigger(false)}
        >
          {busy === "sync" ? <Spinner data-icon="inline-start" /> : <RefreshCwIcon data-icon="inline-start" />}
          Synchronizuj
        </Button>
      </div>
      <p className="type-caption basis-full text-muted-foreground">
        {running
          ? "Synchronizacja tego źródła trwa — widok śledzi ją na żywo."
          : withText === 0
            ? "To źródło nie ma opisów, które model mógłby przeczytać (albo AI było wyłączone przy ostatniej synchronizacji)."
            : `„Klasyfikuj ponownie” wyśle do modelu wszystkie ${formatNumber(withText)} ${plural(withText, "opis", "opisy", "opisów")}, z pominięciem zapamiętanych odpowiedzi (${estimate(withText, status.concurrency)}).`}
      </p>

      <AlertDialog open={confirm} onOpenChange={setConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Sklasyfikować „{name}” od nowa?</AlertDialogTitle>
            <AlertDialogDescription>
              Model przeczyta ponownie {formatNumber(withText)} {plural(withText, "opis", "opisy", "opisów")}, przy{" "}
              {status.concurrency} równoległych zapytaniach to {estimate(withText, status.concurrency)}. Serwer GPU jest
              wspólny, a nowe odpowiedzi zastąpią zapamiętane. Dane podane przez źródło nadal mają pierwszeństwo.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Anuluj</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirm(false);
                void trigger(true);
              }}
            >
              Klasyfikuj
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
