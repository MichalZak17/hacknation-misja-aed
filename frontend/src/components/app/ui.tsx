"use client";

import { AlertTriangleIcon, ExternalLinkIcon, InboxIcon } from "lucide-react";

import { SectionHeading } from "@/components/brand";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  ACCESS_LABEL,
  NO_DATA,
  READINESS_LABEL,
  RUN_KIND_LABEL,
  RUN_STATUS_LABEL,
  label,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  actions,
  meta,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {meta ? <div className="mb-2">{meta}</div> : null}
        <SectionHeading as="h1">{title}</SectionHeading>
        {description ? <p className="type-lead mt-3 max-w-3xl text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function Section({
  title,
  actions,
  children,
  className,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const id = `s-${title.toLowerCase().replace(/[^a-z0-9ąćęłńóśźż]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className={cn("bg-card ring-1 ring-border", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <h2 id={id} className="type-h3 text-hn-heading">
          {title}
        </h2>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function ErrorAlert({ error, title = "Nie udało się pobrać danych" }: { error: ApiError | Error; title?: string }) {
  return (
    <Alert variant="destructive">
      <AlertTriangleIcon />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{error instanceof ApiError ? error.detail : error.message}</AlertDescription>
    </Alert>
  );
}

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2" role="status" aria-label="Ładowanie">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <InboxIcon />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        {description ? <EmptyDescription>{description}</EmptyDescription> : null}
      </EmptyHeader>
    </Empty>
  );
}

const READINESS_VARIANT = {
  ready: "positive",
  attention: "caution",
  expired: "destructive",
  unknown: "secondary",
} as const;

export function ReadinessBadge({ value }: { value: string }) {
  const variant = READINESS_VARIANT[value as keyof typeof READINESS_VARIANT] ?? "secondary";
  return <Badge variant={variant}>{label(READINESS_LABEL, value)}</Badge>;
}

export function AccessBadge({ value }: { value: string }) {
  const variant = value === "public" ? "info" : value === "unknown" ? "secondary" : "outline";
  return <Badge variant={variant}>{label(ACCESS_LABEL, value)}</Badge>;
}

const RUN_VARIANT = { queued: "secondary", running: "info", success: "positive", failed: "destructive" } as const;

export function RunStatusBadge({ status, dryRun }: { status: string; dryRun?: boolean }) {
  const variant = RUN_VARIANT[status as keyof typeof RUN_VARIANT] ?? "secondary";
  return (
    <span className="inline-flex flex-wrap gap-1">
      <Badge variant={variant}>{label(RUN_STATUS_LABEL, status)}</Badge>
      {dryRun ? <Badge variant="outline">Test</Badge> : null}
    </span>
  );
}

export function RunKindLabel({ kind }: { kind: string }) {
  return <span>{label(RUN_KIND_LABEL, kind)}</span>;
}

/** A label / value list; null values read "brak danych" in the subtle colour. */
export function Facts({
  items,
  className,
}: {
  items: { label: string; value: React.ReactNode; hint?: React.ReactNode; wide?: boolean }[];
  className?: string;
}) {
  return (
    <dl className={cn("grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2", className)}>
      {items.map((item) => {
        const empty = item.value === null || item.value === undefined || item.value === "" || item.value === NO_DATA;
        return (
          <div key={item.label} className={cn("min-w-0", item.wide && "sm:col-span-2")}>
            <dt className="type-caption text-muted-foreground">{item.label}</dt>
            <dd className={cn("type-body mt-0.5 break-words", empty ? "text-subtle-foreground italic" : "text-foreground")}>
              {empty ? NO_DATA : item.value}
            </dd>
            {item.hint ? <dd className="type-micro mt-0.5 text-subtle-foreground">{item.hint}</dd> : null}
          </div>
        );
      })}
    </dl>
  );
}

export function Pager({
  count,
  limit,
  offset,
  onChange,
}: {
  count: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const from = count === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, count);
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
      <p className="type-caption text-muted-foreground tabular-nums" aria-live="polite">
        {from}–{to} z {new Intl.NumberFormat("pl-PL").format(count)}
      </p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Poprzednie
        </Button>
        <Button variant="outline" size="sm" disabled={offset + limit >= count} onClick={() => onChange(offset + limit)}>
          Następne
        </Button>
      </div>
    </div>
  );
}

/** Problems that block saving a form, as one alert. API details joined with "; " become separate items. */
export function Problems({ errors, title = "Popraw przed zapisaniem" }: { errors: string[]; title?: string }) {
  if (!errors.length) return null;
  return (
    <Alert variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <ul className="list-disc pl-4">
          {errors
            .flatMap((e) => e.split("; "))
            .map((e) => (
              <li key={e}>{e}</li>
            ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}

/** A link that opens in a new tab, with the icon and the screen-reader note. */
export function ExternalLink({
  href,
  children,
  className,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className={cn("inline-flex items-center gap-1 break-all text-link hover:text-link-hover hover:underline", className)}
    >
      {children}
      <ExternalLinkIcon className="size-3.5 shrink-0" aria-hidden />
      <span className="sr-only">(otwiera się w nowej karcie)</span>
    </a>
  );
}

/** A JSON value in the terminal style: source records, normalised data, connector options. */
export function CodeBlock({ value, className }: { value: unknown; className?: string }) {
  return (
    <pre
      className={cn(
        "type-code max-h-72 overflow-auto bg-hn-terminal p-3 whitespace-pre-wrap break-all text-hn-terminal-foreground",
        className,
      )}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
