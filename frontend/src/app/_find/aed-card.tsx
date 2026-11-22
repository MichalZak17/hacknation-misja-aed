"use client";

import {
  CircleCheckIcon,
  CircleHelpIcon,
  CircleXIcon,
  MapIcon,
  NavigationIcon,
  TriangleAlertIcon,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { NearbyAed } from "@/lib/api";
import { ENUM_LABELS, formatDate } from "@/lib/format";
import { parseOpeningHours } from "@/lib/opening-hours";
import { cn } from "@/lib/utils";

import {
  ACCESS_TEXT,
  availability,
  distanceLine,
  distanceText,
  geoUri,
  osmDirections,
  READINESS_TEXT,
  title,
  type Tone,
  whereText,
} from "./describe";

const TONE: Record<Tone, { box: string; icon: LucideIcon }> = {
  positive: { box: "border-positive-border bg-positive-subtle text-positive-subtle-foreground", icon: CircleCheckIcon },
  caution: { box: "border-caution-border bg-caution-subtle text-caution-subtle-foreground", icon: TriangleAlertIcon },
  negative: { box: "border-negative-border bg-negative-subtle text-negative-subtle-foreground", icon: CircleXIcon },
  neutral: { box: "border-border bg-muted text-foreground", icon: CircleHelpIcon },
};

export function Status({ tone, headline, detail, size = "lg" }: { tone: Tone; headline: string; detail?: string | null; size?: "lg" | "sm" }) {
  const { box, icon: Icon } = TONE[tone];
  return (
    <div className={cn("flex items-start gap-2 border px-3", size === "lg" ? "py-2" : "py-1.5", box)}>
      <Icon aria-hidden className={cn("mt-0.5 shrink-0", size === "lg" ? "size-5" : "size-4")} />
      <p className={size === "lg" ? "type-body" : "type-caption"}>
        <strong className="font-semibold">{headline}</strong>
        {detail ? <span className="block opacity-90">{detail}</span> : null}
      </p>
    </div>
  );
}

const READINESS_COLOR: Record<Tone, string> = {
  positive: "text-positive-subtle-foreground",
  caution: "text-caution-subtle-foreground",
  negative: "text-negative-subtle-foreground",
  neutral: "text-foreground",
};

function ReadinessIcon({ tone }: { tone: Tone }) {
  const Icon = TONE[tone].icon;
  return <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />;
}

function Row({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-3 py-1.5">
      <dt className="type-caption font-semibold text-subtle-foreground">{term}</dt>
      <dd className="type-body min-w-0 break-words text-foreground">{children}</dd>
    </div>
  );
}

const unknown = (text: string) => <span className="text-muted-foreground italic">{text}</span>;

export function AedCard({
  item,
  index,
  from,
  sourceNames,
  selected,
  onShowOnMap,
  now,
}: {
  item: NearbyAed;
  index: number;
  from: { lat: number; lon: number };
  sourceNames: Record<string, string>;
  selected: boolean;
  onShowOnMap: () => void;
  now?: Date;
}) {
  const { aed, distance_m, links } = item;
  const avail = availability(aed, now);
  const readiness = READINESS_TEXT[aed.readiness] ?? READINESS_TEXT.unknown;
  const hours = aed.opening_hours ? parseOpeningHours(aed.opening_hours) : null;
  const where = whereText(aed);
  const address = [aed.address, aed.city].filter(Boolean).join(", ");
  const conditions = (aed.access_conditions ?? []).map((c) => ENUM_LABELS.access_conditions[c] ?? c);
  const headingId = `aed-${aed.id}`;
  const name = title(aed);

  return (
    <article
      aria-labelledby={headingId}
      className={cn(
        "flex flex-col gap-3 border bg-background p-4 transition-colors",
        selected ? "border-hn-crimson ring-1 ring-hn-crimson" : "border-border",
      )}
    >
      <header className="flex items-start gap-3">
        <span
          aria-hidden
          className="flex size-8 shrink-0 items-center justify-center bg-foreground font-sans text-sm font-bold text-background"
        >
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <h3 id={headingId} className="type-h3 break-words text-hn-heading">
            <span className="sr-only">{index + 1}. </span>
            {name}
          </h3>
          <p className="type-body mt-0.5 text-muted-foreground">
            <strong className="font-semibold text-foreground">{distanceText(distance_m)}</strong> {distanceLine(distance_m)}
          </p>
        </div>
      </header>

      <Status tone={avail.tone} headline={avail.headline} detail={avail.detail} />

      <dl className="divide-y divide-border">
        <Row term="Gdzie">
          {where || address ? (
            <>
              {where ? <span className="block">{where}</span> : null}
              {address && address !== name ? <span className="block text-muted-foreground">{address}</span> : null}
              {!where ? <span className="block">{unknown("Brak opisu miejsca w budynku")}</span> : null}
            </>
          ) : (
            unknown("Brak opisu miejsca — kieruj się punktem na mapie")
          )}
        </Row>
        <Row term="Dostęp">
          {ACCESS_TEXT[aed.access] ?? ACCESS_TEXT.unknown}
          {conditions.length ? (
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              {conditions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          ) : null}
        </Row>
        <Row term="Godziny">
          {hours ? (
            <ul>
              {hours.map((h, i) => (
                <li key={i}>
                  {h.when ? <span className="text-muted-foreground">{h.when}: </span> : null}
                  {h.what}
                </li>
              ))}
            </ul>
          ) : aed.opening_hours ? (
            <span className="font-mono text-sm">{aed.opening_hours}</span>
          ) : aed.opening_hours_raw ? (
            <span>„{aed.opening_hours_raw}”</span>
          ) : (
            unknown("Brak danych o godzinach")
          )}
        </Row>
        {aed.readiness !== "unknown" && READINESS_TEXT[aed.readiness] ? (
          <Row term="Czy działa">
            <span className={cn("inline-flex items-start gap-1.5 font-semibold", READINESS_COLOR[readiness.tone])}>
              <ReadinessIcon tone={readiness.tone} />
              {readiness.label}
            </span>
          </Row>
        ) : null}
        <Row term="Sprawdzono">
          {aed.verified_on ? (
            <>
              {formatDate(aed.verified_on)}
              {now && now.getTime() - new Date(aed.verified_on).getTime() > 2 * 365 * 86_400_000 ? (
                <span className="text-muted-foreground"> (ponad 2 lata temu)</span>
              ) : null}
            </>
          ) : (
            unknown("Brak daty sprawdzenia")
          )}
        </Row>
        <Row term="Źródło">{aed.sources.map((s) => sourceNames[s] ?? s).join(", ") || unknown("—")}</Row>
      </dl>

      <div className="flex flex-col gap-2">
        <Button asChild size="lg" variant="default" className="w-full">
          <a href={links.directions} target="_blank" rel="noopener noreferrer">
            <NavigationIcon data-icon="inline-start" aria-hidden />
            Nawiguj pieszo
            <span className="sr-only"> do AED nr {index + 1} (Google Maps, nowe okno)</span>
          </a>
        </Button>
        <Button size="lg" variant="outline" className="w-full" onClick={onShowOnMap}>
          <MapIcon data-icon="inline-start" aria-hidden />
          Pokaż na mapie
        </Button>
      </div>
      <p className="type-caption flex flex-wrap gap-x-4 gap-y-1">
        <a className="inline-flex min-h-6 items-center text-link hover:underline" href={geoUri(aed)}>
          Otwórz w aplikacji mapy
        </a>
        <a
          className="inline-flex min-h-6 items-center text-link hover:underline"
          href={osmDirections(aed, from)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Trasa w OpenStreetMap<span className="sr-only"> (nowe okno)</span>
        </a>
        <a
          className="inline-flex min-h-6 items-center text-link hover:underline"
          href={`/zglos?aed=${encodeURIComponent(aed.id)}`}
        >
          Zgłoś błąd<span className="sr-only"> w danych AED nr {index + 1}</span>
        </a>
      </p>
    </article>
  );
}
