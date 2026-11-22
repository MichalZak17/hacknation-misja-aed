"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownIcon, LocateFixedIcon, NavigationIcon, PhoneIcon, SearchIcon } from "lucide-react";

import { ErrorAlert } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

import { AedCard, Status as AvailabilityStatus } from "./aed-card";
import { availability, distanceLine, distanceText, FAR_M, title, walkingText, whereText } from "./describe";
import { geocode, GeocodeError, type Place } from "./geocode";
import { PublicMap, type Origin } from "./public-map";

const focusWhite = "outline-none focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-white";

function Emergency() {
  return (
    <section aria-labelledby="emergency-heading" className="bg-hn-crimson text-white">
      <div className="flex items-center gap-3 py-2.5 pr-[max(1rem,env(safe-area-inset-right))] pl-[max(1rem,env(safe-area-inset-left))] md:px-6">
        <PhoneIcon aria-hidden className="hidden size-6 shrink-0 sm:block lg:hidden xl:block" />
        {/* Phones and the narrow desktop column get the short line, so the banner stays one row */}
        <h2 id="emergency-heading" className="min-w-0 flex-1 text-base leading-tight font-bold sm:text-lg">
          <span className="sm:hidden lg:inline xl:hidden">Nagły wypadek?</span>
          <span className="hidden sm:inline lg:hidden xl:inline">W nagłym wypadku dzwoń 112</span>
        </h2>
        <a
          href="tel:112"
          className={cn(
            "inline-flex h-11 shrink-0 items-center gap-2 bg-white px-5 text-base font-bold text-[#b8002e] hover:bg-white/90",
            focusWhite,
          )}
        >
          <PhoneIcon aria-hidden className="size-4" />
          Zadzwoń 112
        </a>
      </div>
    </section>
  );
}

type Status = { kind: "idle" } | { kind: "locating" } | { kind: "geocoding" } | { kind: "error"; text: string };

function geoErrorText(error: GeolocationPositionError) {
  if (error.code === error.PERMISSION_DENIED)
    return "Brak zgody na lokalizację. Wpisz adres albo dotknij mapy. Zgodę możesz zmienić w ustawieniach przeglądarki.";
  if (error.code === error.TIMEOUT)
    return "Ustalanie położenia trwa zbyt długo. Spróbuj jeszcze raz, wpisz adres albo dotknij mapy.";
  return "Nie udało się ustalić położenia. Wpisz adres albo dotknij mapy.";
}

export function FindAed() {
  const [origin, setOrigin] = useState<Origin | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [address, setAddress] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [publicOnly, setPublicOnly] = useState(false);
  const [limit, setLimit] = useState(5);
  const [selected, setSelected] = useState<string | null>(null);
  // Set when results arrive and every minute after: never read during the prerender
  const [now, setNow] = useState<Date | null>(null);
  const answerHeading = useRef<HTMLHeadingElement>(null);
  const mapBox = useRef<HTMLDivElement>(null);
  const focusResults = useRef(false);

  const sources = useApi("sources", api.sources);
  const sourceNames = useMemo(
    () => Object.fromEntries((sources.data ?? []).map((s) => [s.slug, s.name])),
    [sources.data],
  );

  const key = origin ? `nearby:${origin.lat}:${origin.lon}:${publicOnly}:${limit}` : null;
  const nearby = useApi(key, async () => {
    const found = await api.nearby({ lat: origin!.lat, lon: origin!.lon, limit, access: publicOnly ? "public" : undefined });
    setNow(new Date());
    return found;
  });
  const results = useMemo(() => (origin ? (nearby.data?.items ?? []) : []), [origin, nearby.data]);

  // "Open now" stays true to the clock while the page is open
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  // After a search the person started, move focus (and the screen) to the results
  useEffect(() => {
    if (!nearby.loading && nearby.data && focusResults.current) {
      focusResults.current = false;
      const heading = answerHeading.current;
      if (!heading) return;
      heading.focus({ preventScroll: true });
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      heading.closest("section")?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
    }
  }, [nearby.loading, nearby.data]);

  function pick(lat: number, lon: number, label: string, focus = true) {
    focusResults.current = focus;
    setSelected(null);
    setLimit(5);
    setOrigin({ lat: Math.round(lat * 1e5) / 1e5, lon: Math.round(lon * 1e5) / 1e5, label });
  }

  function locate() {
    setPlaces([]);
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      setStatus({ kind: "error", text: "Ta przeglądarka nie udostępnia lokalizacji. Wpisz adres albo dotknij mapy." });
      return;
    }
    if (!window.isSecureContext) {
      setStatus({
        kind: "error",
        text: "Lokalizacja działa tylko na stronie otwartej przez https. Wpisz adres albo dotknij mapy.",
      });
      return;
    }
    setStatus({ kind: "locating" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setStatus({ kind: "idle" });
        setAccuracy(pos.coords.accuracy);
        pick(pos.coords.latitude, pos.coords.longitude, "Twoja lokalizacja");
      },
      (error) => setStatus({ kind: "error", text: geoErrorText(error) }),
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 },
    );
  }

  async function searchAddress(event: React.FormEvent) {
    event.preventDefault();
    const text = address.trim();
    if (text.length < 3) {
      setStatus({ kind: "error", text: "Wpisz co najmniej 3 znaki: ulicę z numerem i miejscowość albo samą miejscowość." });
      return;
    }
    setStatus({ kind: "geocoding" });
    try {
      const found = await geocode(text);
      if (!found.length) {
        setPlaces([]);
        setStatus({ kind: "error", text: "Nie znaleźliśmy takiego miejsca w Polsce. Spróbuj dopisać miejscowość." });
        return;
      }
      setStatus({ kind: "idle" });
      setPlaces(found);
      setAccuracy(null);
      pick(found[0].lat, found[0].lon, found[0].label);
    } catch (e) {
      setStatus({ kind: "error", text: e instanceof GeocodeError ? e.message : "Nie udało się wyszukać adresu." });
    }
  }

  function onMapPick(lat: number, lon: number) {
    setPlaces([]);
    setAccuracy(null);
    setStatus({ kind: "idle" });
    pick(lat, lon, "Miejsce wskazane na mapie", false);
  }

  function showOnMap(id: string) {
    setSelected(id);
    const box = mapBox.current?.getBoundingClientRect();
    // Phones: the map sits above the list, so bring it back into view
    if (box && (box.bottom < 80 || box.top > window.innerHeight * 0.5)) {
      mapBox.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function selectFromMap(id: string) {
    setSelected(id);
    document.getElementById(`aed-${id}`)?.closest("article")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  const answer = useMemo(() => {
    if (!results.length || !now) return null;
    const first = results[0];
    const firstAvail = availability(first.aed, now);
    const openIndex =
      firstAvail.open.state === "open" ? 0 : results.findIndex((r) => availability(r.aed, now).open.state === "open");
    const note =
      openIndex === 0
        ? null
        : openIndex > 0
          ? `Najbliższy otwarty teraz według godzin: nr ${openIndex + 1}, ${distanceText(results[openIndex].distance_m)}.`
          : `Żaden z ${results.length} najbliższych AED nie ma potwierdzonych godzin otwarcia na tę chwilę.`;
    const walk = walkingText(first.distance_m);
    const text = `Najbliższy AED: ${distanceText(first.distance_m)}${walk ? `, ${walk}` : ""} — ${firstAvail.headline.toLowerCase()}.${note ? ` ${note}` : ""}`;
    const where = whereText(first.aed);
    return { first, firstAvail, note, text, where };
  }, [results, now]);

  const busy = status.kind === "locating" || status.kind === "geocoding" || nearby.loading;
  const liveText =
    status.kind === "locating"
      ? "Ustalanie położenia…"
      : status.kind === "geocoding"
        ? "Szukanie adresu…"
        : nearby.loading
          ? "Szukanie najbliższych AED…"
          : status.kind === "error"
            ? status.text
            : answer
              ? `Znaleziono ${results.length} AED. ${answer.text}`
              : "";

  return (
    <div className="grid grid-cols-1 lg:min-h-[calc(100svh-3.5rem)] lg:grid-cols-[minmax(22rem,28rem)_1fr] lg:grid-rows-[auto_auto_1fr] xl:grid-cols-[32rem_1fr]">
      <div className="bg-background lg:col-start-1 lg:border-r lg:border-border">
        <Emergency />

        <section aria-labelledby="find-heading" className="flex flex-col gap-4 px-4 py-5 md:px-6">
          <div>
            <h1 id="find-heading" className="type-h1 text-hn-heading">
              Znajdź najbliższy defibrylator AED
            </h1>
            <p className="type-body mt-1 text-muted-foreground">Gdzie jest, czy jest teraz dostępny i czy działa.</p>
          </div>

          <div>
            <Button
              size="lg"
              variant="cta"
              className="h-12 w-full text-base"
              onClick={locate}
              disabled={status.kind === "locating"}
            >
              {status.kind === "locating" ? <Spinner /> : <LocateFixedIcon data-icon="inline-start" aria-hidden />}
              Pokaż AED w pobliżu mnie
            </Button>
          </div>

          {/* suppressHydrationWarning: the Google app's browser tags forms and inputs with __gcruniqueid before hydration */}
          <form
            onSubmit={searchAddress}
            className="flex flex-col gap-1.5"
            role="search"
            aria-label="Szukaj AED przy adresie"
            suppressHydrationWarning
          >
            <Label htmlFor="address" className="type-body font-semibold">
              Albo wpisz adres
            </Label>
            <div className="flex gap-2">
              <Input
                suppressHydrationWarning
                id="address"
                name="address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="np. Marszałkowska 10, Warszawa"
                autoComplete="street-address"
                enterKeyHint="search"
                className="h-11 text-base md:text-base"
              />
              <Button type="submit" size="lg" variant="outline" disabled={status.kind === "geocoding"}>
                {status.kind === "geocoding" ? <Spinner /> : <SearchIcon data-icon="inline-start" aria-hidden />}
                Szukaj
              </Button>
            </div>
          </form>

          {places.length > 1 ? (
            <div>
              <p className="type-caption font-semibold text-subtle-foreground">Inne pasujące miejsca:</p>
              <ul className="mt-1 flex flex-col">
                {places.slice(1).map((p) => (
                  <li key={`${p.lat},${p.lon}`}>
                    <button
                      type="button"
                      onClick={() => pick(p.lat, p.lon, p.label)}
                      className="type-caption flex min-h-11 w-full items-center text-left text-link hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      {p.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="flex items-center gap-3">
            <Checkbox
              id="public-only"
              checked={publicOnly}
              onCheckedChange={(v) => setPublicOnly(v === true)}
              className="size-5"
            />
            <Label htmlFor="public-only" className="type-body min-h-11 cursor-pointer">
              Tylko ogólnodostępne
            </Label>
          </div>

          <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
            {liveText}
          </p>
          {status.kind === "error" ? (
            // Announced by the status region above; shown here for sighted users
            <p aria-hidden className="type-body border border-caution-border bg-caution-subtle px-3 py-2 text-caution-subtle-foreground">
              {status.text}
            </p>
          ) : null}
          {nearby.error ? <ErrorAlert error={nearby.error} title="Nie udało się wyszukać AED" /> : null}
          {origin && busy && !results.length ? (
            <p className="type-body inline-flex items-center gap-2 text-muted-foreground">
              <Spinner /> Szukanie najbliższych AED…
            </p>
          ) : null}

          {answer ? (
            <section
              aria-labelledby="answer-heading"
              className={cn("flex scroll-mt-20 flex-col gap-3 border-2 border-foreground p-4", nearby.loading && "opacity-60")}
            >
              <div>
                <h2 id="answer-heading" ref={answerHeading} tabIndex={-1} className="type-caption font-semibold tracking-wide text-subtle-foreground uppercase outline-none">
                  Najbliższy AED
                </h2>
                <p className="type-h3 mt-1 break-words text-hn-heading">{title(answer.first.aed)}</p>
                {answer.where ? <p className="type-body mt-1 break-words text-foreground">{answer.where}</p> : null}
                <p className="type-body text-muted-foreground">
                  <strong className="text-lg font-bold text-foreground">{distanceText(answer.first.distance_m)}</strong>{" "}
                  {distanceLine(answer.first.distance_m)}
                </p>
              </div>
              {answer.first.distance_m > FAR_M ? (
                <p className="type-body border border-caution-border bg-caution-subtle px-3 py-2 font-medium text-caution-subtle-foreground">
                  Najbliższy znany AED jest daleko. Dzwoń 112 i zacznij uciskanie klatki piersiowej — dyspozytor wyśle pomoc.
                  W pobliżu może być AED, którego nie ma jeszcze w danych.
                </p>
              ) : null}
              <AvailabilityStatus tone={answer.firstAvail.tone} headline={answer.firstAvail.headline} detail={answer.firstAvail.detail} />
              {answer.note ? <p className="type-body font-medium text-foreground">{answer.note}</p> : null}
              <div className="flex flex-col gap-2">
                <Button asChild size="lg" className="h-12 w-full text-base">
                  <a href={answer.first.links.directions} target="_blank" rel="noopener noreferrer">
                    <NavigationIcon data-icon="inline-start" aria-hidden />
                    Nawiguj pieszo
                    <span className="sr-only"> do najbliższego AED (Google Maps, nowe okno)</span>
                  </a>
                </Button>
                <Button asChild size="lg" variant="outline" className="h-12 w-full">
                  <a href="#results-heading">
                    <ArrowDownIcon data-icon="inline-start" aria-hidden />
                    Inne AED w pobliżu
                  </a>
                </Button>
              </div>
            </section>
          ) : null}
        </section>
      </div>

      <div
        ref={mapBox}
        className="h-[55svh] min-h-[20rem] lg:col-start-2 lg:row-span-3 lg:row-start-1 lg:h-auto lg:min-h-0"
      >
        <div className="h-full lg:sticky lg:top-14 lg:h-[calc(100svh-3.5rem)]">
          <PublicMap origin={origin} results={results} selected={selected} onPick={onMapPick} onSelect={selectFromMap} />
        </div>
      </div>

      {origin && results.length ? (
        <section
          aria-labelledby="results-heading"
          className="flex scroll-mt-16 flex-col gap-3 px-4 py-5 md:px-6 lg:col-start-1 lg:border-r lg:border-border"
          id="results"
        >
          <div>
            <h2 id="results-heading" tabIndex={-1} className="type-h2 scroll-mt-16 text-hn-heading outline-none">
              Najbliższe AED
            </h2>
            <p className="type-caption mt-1 break-words text-muted-foreground">
              Od: {origin.label}
              {accuracy && accuracy > 50 ? ` (dokładność ok. ${Math.round(accuracy)} m)` : ""}
              {publicOnly ? " · tylko ogólnodostępne" : ""}
            </p>
          </div>
          <ol className={cn("flex flex-col gap-3", nearby.loading && "opacity-60")} aria-busy={nearby.loading}>
            {results.map((item, i) => (
              <li key={item.aed.id}>
                <AedCard
                  item={item}
                  index={i}
                  from={origin}
                  sourceNames={sourceNames}
                  selected={selected === item.aed.id}
                  onShowOnMap={() => showOnMap(item.aed.id)}
                  now={now ?? undefined}
                />
              </li>
            ))}
          </ol>
          {limit < 10 ? (
            <Button variant="outline" size="lg" onClick={() => setLimit(10)} disabled={nearby.loading}>
              Pokaż więcej AED (do 10)
            </Button>
          ) : null}
          <p className="type-caption text-subtle-foreground">
            Odległość w linii prostej. Dane mogą być nieaktualne.
          </p>
        </section>
      ) : (
        <div className="hidden lg:col-start-1 lg:block lg:border-r lg:border-border" />
      )}
    </div>
  );
}
