"use client";

import Link from "next/link";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeftIcon, ChevronRightIcon, SparklesIcon } from "lucide-react";
import { Tabs as TabsPrimitive } from "radix-ui";

import { SectionHeading } from "@/components/brand";
import { ErrorAlert, LoadingRows } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { api, type Integration } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { deliveryLabel, health, plural, pollInterval, type Tone } from "@/lib/integrations";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

import { HealthBadge } from "../_components/health";
import { RunHistory } from "../_components/run-history";
import { SourceRecords } from "../_components/source-records";
import { OperatorUpload, SourceSettings } from "../_components/source-settings";
import { SyncActions } from "../_components/sync-actions";

const TABS = ["history", "records", "settings"] as const;
type Tab = (typeof TABS)[number];

export function IntegrationDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [pollMs, setPollMs] = useState<number | undefined>(undefined);
  const integration = useApi(`int:${slug}`, () => api.integration(slug), { interval: pollMs });
  const next = pollInterval(integration.data ? [integration.data] : undefined);
  if (next !== pollMs) setPollMs(next);
  const [tab, setTab] = useTab();

  const reloadAll = () => void integration.reload();

  if (integration.error && !integration.data) return <ErrorAlert error={integration.error} />;
  const i = integration.data;
  if (!i) return <LoadingRows rows={8} />;

  return (
    <>
      <Link
        href="/integrations"
        className="type-caption mb-3 inline-flex items-center gap-1 text-muted-foreground hover:text-foreground hover:underline"
      >
        <ArrowLeftIcon aria-hidden className="size-3.5" />
        Wszystkie źródła
      </Link>
      <header className="mb-6">
        <SectionHeading as="h1">{i.name}</SectionHeading>
        <p className="type-lead mt-3 max-w-3xl text-muted-foreground">
          {[i.publisher, deliveryLabel(i), `Priorytet ${i.priority}`]
            .filter(Boolean)
            .join(". ")}
          .
        </p>
        {i.description ? <p className="type-body mt-1 max-w-3xl text-subtle-foreground">{i.description}</p> : null}
      </header>

      <StatusPanel integration={i} onQueued={reloadAll} />
      {i.accepts_upload ? <OperatorUpload integration={i} onUploaded={reloadAll} /> : null}
      {i.records || i.removed_records ? <Pipeline integration={i} /> : null}

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="mt-6 gap-0 bg-card ring-1 ring-border">
        <TabsPrimitive.List aria-label="Widok źródła" className="flex gap-6 border-b border-border px-4">
          <DetailTab value="history">Historia</DetailTab>
          <DetailTab value="records">
            Rekordy <span className="font-normal text-muted-foreground tabular-nums">{formatNumber(i.records)}</span>
          </DetailTab>
          <DetailTab value="settings">Ustawienia</DetailTab>
        </TabsPrimitive.List>
        <div className="p-4">
          <TabsContent value="history">
            <RunHistory
              slug={i.slug}
              version={`${i.last_run?.id ?? 0}:${i.last_run?.status ?? ""}`}
              interval={i.running ? pollMs : undefined}
            />
          </TabsContent>
          <TabsContent value="records">
            <SourceRecords slug={i.slug} invalid={i.invalid_records} />
          </TabsContent>
          <TabsContent value="settings">
            <SourceSettings integration={i} onSaved={reloadAll} />
          </TabsContent>
        </div>
      </Tabs>
    </>
  );
}

/** The open tab lives in the URL (?tab=records) so a demo link or a reload lands on the same view. */
function useTab(): [Tab, (t: Tab) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const raw = params.get("tab");
  const tab: Tab = TABS.includes(raw as Tab) ? (raw as Tab) : "history";
  const set = (t: Tab) => router.replace(t === "history" ? pathname : `${pathname}?tab=${t}`, { scroll: false });
  return [tab, set];
}

function DetailTab({ value, children }: { value: Tab; children: React.ReactNode }) {
  return (
    <TabsPrimitive.Trigger
      value={value}
      className="type-body -mb-px h-11 border-b-2 border-transparent font-semibold whitespace-nowrap text-muted-foreground outline-none hover:text-foreground focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring data-[state=active]:border-hn-crimson data-[state=active]:text-foreground"
    >
      {children}
    </TabsPrimitive.Trigger>
  );
}

const TONE_BAR: Record<Tone, string> = {
  positive: "bg-positive",
  info: "bg-info",
  caution: "bg-caution",
  negative: "bg-destructive",
  neutral: "bg-disabled-foreground",
};

/** What state the source is in, in one sentence, next to the actions that change it. */
function StatusPanel({ integration: i, onQueued }: { integration: Integration; onQueued: () => void }) {
  const h = health(i);
  return (
    <section aria-label="Stan źródła" className="relative mb-6 bg-card ring-1 ring-border">
      <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1", TONE_BAR[h.tone])} />
      <div className="flex flex-col gap-4 py-4 pr-4 pl-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <HealthBadge tone={h.tone} label={h.label} />
          <p className="type-body mt-2 max-w-2xl" aria-live="polite">
            {h.sentence}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SyncActions integration={i} onQueued={onQueued} />
          <Button asChild size="sm" variant="ghost">
            <Link href={`/ai?source=${encodeURIComponent(i.slug)}`}>
              <SparklesIcon data-icon="inline-start" />
              Klasyfikacja AI
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

/**
 * The path from the source to the registry: records the source holds, the ones that passed validation, and the AED
 * entries they became. Each step says why the number dropped.
 */
function Pipeline({ integration: i }: { integration: Integration }) {
  const merged = Math.max(0, i.valid_records - i.devices);
  const steps = [
    {
      title: "W źródle",
      value: i.records,
      unit: plural(i.records, "rekord", "rekordy", "rekordów"),
      note: i.removed_records
        ? `${formatNumber(i.removed_records)} ${plural(i.removed_records, "zniknął", "zniknęły", "zniknęło")} ze źródła`
        : "aktualne",
    },
    {
      title: "Po walidacji",
      value: i.valid_records,
      unit: plural(i.valid_records, "poprawny", "poprawne", "poprawnych"),
      note: i.invalid_records ? `${formatNumber(i.invalid_records)} odrzuconych` : "nic nie odrzucono",
      warn: i.invalid_records > 0,
    },
    {
      title: "W rejestrze AED",
      value: i.devices,
      unit: plural(i.devices, "urządzenie", "urządzenia", "urządzeń"),
      note: merged
        ? `${formatNumber(merged)} ${plural(merged, "rekord to duplikat", "rekordy to duplikaty", "rekordów to duplikaty")} w obrębie źródła`
        : "każdy rekord to osobne urządzenie",
    },
  ];
  return (
    <section aria-label="Od źródła do rejestru" className="bg-card ring-1 ring-border">
      <ol className="grid grid-cols-1 sm:grid-cols-3">
        {steps.map((s, n) => (
          <li key={s.title} className="relative border-border px-4 py-3 max-sm:border-t max-sm:first:border-t-0 sm:border-l sm:first:border-l-0">
            {n > 0 ? (
              <ChevronRightIcon
                aria-hidden
                className="absolute top-1/2 -left-2.5 size-5 -translate-y-1/2 bg-card text-subtle-foreground max-sm:hidden"
              />
            ) : null}
            <p className="type-caption text-muted-foreground">{s.title}</p>
            <p className="mt-0.5 flex items-baseline gap-1.5">
              <span className="font-display text-[2rem] leading-none tabular-nums">{formatNumber(s.value)}</span>
              <span className="type-body text-muted-foreground">{s.unit}</span>
            </p>
            <p className={cn("type-micro mt-1", s.warn ? "text-caution-subtle-foreground dark:text-caution" : "text-subtle-foreground")}>
              {s.note}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
