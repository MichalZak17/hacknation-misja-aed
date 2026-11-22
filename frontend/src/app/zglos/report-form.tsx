"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CircleCheckIcon, LocateFixedIcon, PhoneIcon, SendIcon } from "lucide-react";

import { MetaLabel, SectionHeading } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { api, REPORT_KIND_LABEL, ReportError, reportsApi, type DeviceDetail, type ReportKind } from "@/lib/api";
import { cn } from "@/lib/utils";

const MAX = 2000;
const POLAND = { minLat: 49.0, maxLat: 54.84, minLon: 14.07, maxLon: 24.15 };

/** What people most often see first; the owner's offer last. */
const KINDS: { value: ReportKind; hint: string }[] = [
  { value: "not_working", hint: "Miga lampka, brak elektrod, rozładowana bateria, uszkodzona szafka." },
  { value: "locked", hint: "Szafka lub budynek zamknięte, choć mapa mówi, że AED jest dostępny." },
  { value: "wrong_location", hint: "Punkt na mapie jest w innym miejscu niż urządzenie." },
  { value: "wrong_details", hint: "Złe godziny, warunki dostępu albo opis miejsca." },
  { value: "missing_aed", hint: "Znasz AED, którego nie ma na mapie." },
  { value: "holder_update", hint: "Odpowiadasz za AED i chcesz uzupełnić lub poprawić jego dane." },
];

/** What makes a report useful, by kind: precise place, hours and access, readiness. */
const DESCRIPTION_HINT: Record<ReportKind, string> = {
  not_working: "Co widać na urządzeniu? Kiedy to zauważyłeś(-aś)?",
  locked: "Kiedy było zamknięte (dzień, godzina)? Czy ktoś na miejscu ma klucz lub kod?",
  wrong_location: "Gdzie AED jest naprawdę: budynek, wejście, piętro, przy czym wisi.",
  wrong_details: "Co jest błędne i jak powinno być, np. godziny otwarcia budynku.",
  missing_aed: "Nazwa miejsca i adres, gdzie dokładnie wisi (wejście, piętro), w jakich godzinach jest dostępny.",
  holder_update:
    "Jaki to AED (adres, miejsce), co chcesz przekazać: godziny, dostęp, model, daty przeglądów i wymiany elektrod.",
};

type Field = "kind" | "device_id" | "location" | "description" | "contact_email";
type Errors = Partial<Record<Field, string>>;

/** The element each error points at: the summary's links and the focus after a failed send. */
const TARGET: Record<Field, string> = {
  kind: `kind-${KINDS[0].value}`,
  device_id: "device_id",
  location: "lat",
  description: "description",
  contact_email: "contact_email",
};
const ORDER: Field[] = ["kind", "device_id", "location", "description", "contact_email"];

function parseCoord(value: string): number | null {
  const n = Number(value.trim().replace(",", "."));
  return value.trim() && Number.isFinite(n) ? n : null;
}

function validate(v: { kind: ReportKind | ""; lat: string; lon: string; description: string; email: string }): Errors {
  const errors: Errors = {};
  if (!v.kind) errors.kind = "Wybierz, czego dotyczy zgłoszenie.";
  const lat = parseCoord(v.lat);
  const lon = parseCoord(v.lon);
  if ((v.lat.trim() && lat === null) || (v.lon.trim() && lon === null)) {
    errors.location = "Współrzędne wpisz jako liczby, np. 52.2297 i 21.0122.";
  } else if ((lat === null) !== (lon === null)) {
    errors.location = "Podaj obie współrzędne albo żadnej.";
  } else if (
    lat !== null &&
    lon !== null &&
    (lat < POLAND.minLat || lat > POLAND.maxLat || lon < POLAND.minLon || lon > POLAND.maxLon)
  ) {
    errors.location = "To miejsce leży poza Polską. Szerokość to 49–55, długość 14–24.";
  }
  if (!v.description.trim()) errors.description = "Opisz krótko, co się nie zgadza.";
  else if (v.description.length > MAX) errors.description = `Opis może mieć najwyżej ${MAX} znaków.`;
  const email = v.email.trim();
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.contact_email = "Wpisz adres w postaci nazwa@domena.pl albo zostaw pole puste.";
  }
  return errors;
}

function geoErrorText(error: GeolocationPositionError) {
  if (error.code === error.PERMISSION_DENIED) return "Nie zezwolono na lokalizację. Możesz wpisać współrzędne ręcznie.";
  if (error.code === error.TIMEOUT) return "Lokalizacja trwała zbyt długo. Spróbuj ponownie albo wpisz współrzędne.";
  return "Nie udało się ustalić lokalizacji. Wpisz współrzędne ręcznie.";
}

const describedBy = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(" ") || undefined;

function ErrorText({ id, children }: { id: string; children?: string }) {
  if (!children) return null;
  return (
    <p id={id} className="type-body font-medium text-negative">
      <span className="sr-only">Błąd: </span>
      {children}
    </p>
  );
}

/** The number a link from an AED card passes: /zglos?aed=AED-PL-000123 */
function aedFromQuery(value: string | null) {
  const id = value?.trim().toUpperCase();
  return id && /^AED-PL-\d+$/.test(id) ? id : "";
}

export function ReportForm() {
  const params = useSearchParams();
  const [initialAed] = useState(() => aedFromQuery(params.get("aed")));
  const [kind, setKind] = useState<ReportKind | "">("");
  const [deviceId, setDeviceId] = useState(initialAed);
  const [device, setDevice] = useState<DeviceDetail | null>(null);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [locate, setLocate] = useState<{ busy: boolean; text: string }>({ busy: false, text: "" });
  const [focusTick, setFocusTick] = useState(0);

  const summaryRef = useRef<HTMLDivElement>(null);
  const doneRef = useRef<HTMLHeadingElement>(null);

  // Show which AED a link from the map is about
  useEffect(() => {
    if (!initialAed) return;
    api
      .device(initialAed)
      .then(setDevice)
      .catch(() => setDevice(null));
  }, [initialAed]);

  // Move focus after the render that shows the error summary or the thank-you
  useEffect(() => {
    if (!focusTick) return;
    if (state === "sent") doneRef.current?.focus();
    else summaryRef.current?.focus();
  }, [focusTick, state]);

  function fillMyLocation() {
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      setLocate({ busy: false, text: "Ta przeglądarka nie udostępnia lokalizacji. Wpisz współrzędne ręcznie." });
      return;
    }
    if (!window.isSecureContext) {
      setLocate({ busy: false, text: "Lokalizacja działa tylko na stronie otwartej przez https." });
      return;
    }
    setLocate({ busy: true, text: "Ustalam lokalizację…" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLon(pos.coords.longitude.toFixed(6));
        setErrors((e) => ({ ...e, location: undefined }));
        setLocate({
          busy: false,
          text: `Wpisano Twoją lokalizację (dokładność ok. ${Math.max(1, Math.round(pos.coords.accuracy))} m).`,
        });
      },
      (error) => setLocate({ busy: false, text: geoErrorText(error) }),
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 30_000 },
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    const found = validate({ kind, lat, lon, description, email });
    setErrors(found);
    if (Object.keys(found).length) {
      setFocusTick((t) => t + 1);
      return;
    }
    setState("sending");
    try {
      await reportsApi.create({
        kind: kind as ReportKind,
        device_id: deviceId.trim() || null,
        lat: parseCoord(lat),
        lon: parseCoord(lon),
        description: description.trim(),
        contact_email: email.trim() || null,
        website,
      });
      setState("sent");
    } catch (e) {
      setState("idle");
      if (e instanceof ReportError && Object.keys(e.errors).length) {
        setErrors(e.errors as Errors);
      } else {
        setFormError(e instanceof ReportError ? e.detail : "Nie udało się wysłać zgłoszenia. Spróbuj ponownie.");
      }
    }
    setFocusTick((t) => t + 1);
  }

  function reset() {
    setKind("");
    setDeviceId("");
    setDevice(null);
    setLat("");
    setLon("");
    setDescription("");
    setEmail("");
    setErrors({});
    setFormError(null);
    setLocate({ busy: false, text: "" });
    setState("idle");
    window.history.replaceState(null, "", "/zglos");
  }

  const errorList = ORDER.filter((f) => errors[f]);
  const deviceName = device ? device.name ?? device.building_name : null;
  const deviceAddress = device ? [device.address, device.city].filter(Boolean).join(", ") : "";

  return (
    <div className="mx-auto w-full max-w-2xl">
      <MetaLabel prompt>Otwarte AED</MetaLabel>
      <SectionHeading as="h1" className="mt-2">
        Zgłoś AED lub błąd
      </SectionHeading>

      {state === "sent" ? (
        <section aria-labelledby="done-title" className="mt-6 border border-positive-border bg-positive-subtle p-5">
          <div className="flex items-start gap-3 text-positive-subtle-foreground">
            <CircleCheckIcon aria-hidden className="mt-1 size-6 shrink-0" />
            <div>
              <h2 id="done-title" ref={doneRef} tabIndex={-1} className="type-h2 outline-none">
                Dziękujemy, zgłoszenie dotarło
              </h2>
              <p className="type-body mt-2">Co dalej:</p>
              <ol className="type-body mt-1 list-decimal space-y-1 pl-5">
                <li>Opiekun zbioru sprawdzi zgłoszenie, zwykle w ciągu kilku dni roboczych.</li>
                <li>
                  Jeśli potwierdzimy błąd, poprawimy dane razem z dysponentem AED lub źródłem danych. Poprawka trafi do
                  mapy i do otwartego zbioru na dane.gov.pl.
                </li>
                <li>Jeśli podano e-mail, napiszemy tylko wtedy, gdy będziemy potrzebować szczegółów.</li>
              </ol>
              <p className="type-body mt-2">Samo zgłoszenie nie jest publikowane.</p>
            </div>
          </div>
          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/">Wróć do mapy AED</Link>
            </Button>
            <Button size="lg" variant="outline" onClick={reset}>
              Wyślij kolejne zgłoszenie
            </Button>
          </div>
        </section>
      ) : (
        <>
          <p className="type-lead mt-4 text-muted-foreground">
            Brakuje defibrylatora na mapie, stoi gdzie indziej, nie działa albo jest zamknięty? Daj znać. Jesteś
            dysponentem AED? Przekaż nam jego dane.
          </p>
          <p className="type-body mt-3 flex items-start gap-2 text-foreground">
            <PhoneIcon aria-hidden className="mt-1 size-4 shrink-0 text-hn-crimson" />
            <span>
              <strong className="font-semibold">W nagłym wypadku dzwoń 112.</strong> Ten formularz nie wzywa pomocy.
            </span>
          </p>

          {errorList.length || formError ? (
            <div
              ref={summaryRef}
              tabIndex={-1}
              aria-labelledby="summary-title"
              className="mt-6 border-2 border-negative-border bg-negative-subtle p-4 text-negative-subtle-foreground outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <h2 id="summary-title" className="type-h4">
                {formError ? "Nie wysłano zgłoszenia" : "Popraw zaznaczone pola"}
              </h2>
              {formError ? <p className="type-body mt-1">{formError}</p> : null}
              {errorList.length ? (
                <ul className="type-body mt-2 list-disc space-y-1 pl-5">
                  {errorList.map((f) => (
                    <li key={f}>
                      <a
                        href={`#${TARGET[f]}`}
                        className="underline underline-offset-4"
                        onClick={(e) => {
                          e.preventDefault();
                          document.getElementById(TARGET[f])?.focus();
                        }}
                      >
                        {errors[f]}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          <form onSubmit={submit} noValidate className="mt-6 flex flex-col gap-7" aria-label="Zgłoszenie AED">
            <fieldset aria-describedby={describedBy(errors.kind && "kind-error")} className="flex flex-col gap-2">
              <legend className="type-h4 mb-2 text-foreground">
                Czego dotyczy zgłoszenie? <span className="type-body font-normal text-muted-foreground">(wymagane)</span>
              </legend>
              <ErrorText id="kind-error">{errors.kind}</ErrorText>
              <div className="grid gap-2 sm:grid-cols-2">
                {KINDS.map((k) => {
                  const id = `kind-${k.value}`;
                  return (
                    <label
                      key={k.value}
                      htmlFor={id}
                      className={cn(
                        "flex min-h-11 cursor-pointer items-start gap-3 border bg-background p-3 transition-colors hover:bg-accent has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ring",
                        kind === k.value ? "border-hn-crimson ring-1 ring-hn-crimson" : "border-border",
                        errors.kind && "border-negative-border",
                      )}
                    >
                      <input
                        id={id}
                        type="radio"
                        name="kind"
                        value={k.value}
                        checked={kind === k.value}
                        onChange={() => {
                          setKind(k.value);
                          setErrors((e) => ({ ...e, kind: undefined }));
                        }}
                        aria-describedby={`${id}-hint`}
                        className="mt-1 size-4 shrink-0 accent-hn-crimson"
                      />
                      <span className="min-w-0">
                        <span className="type-body block font-semibold text-foreground">
                          {REPORT_KIND_LABEL[k.value]}
                        </span>
                        <span id={`${id}-hint`} className="type-caption block text-muted-foreground">
                          {k.hint}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <div className="flex flex-col gap-2">
              <label htmlFor="device_id" className="type-h4 text-foreground">
                Numer AED <span className="type-body font-normal text-muted-foreground">(nieobowiązkowy)</span>
              </label>
              <p id="device_id-hint" className="type-caption text-muted-foreground">
                Jeśli zgłaszasz AED z mapy, numer jest na jego karcie, np. AED-PL-000123.
              </p>
              <Input
                id="device_id"
                name="device_id"
                value={deviceId}
                onChange={(e) => {
                  setDeviceId(e.target.value);
                  setDevice(null);
                  setErrors((er) => ({ ...er, device_id: undefined }));
                }}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={errors.device_id ? true : undefined}
                aria-describedby={describedBy(
                  "device_id-hint",
                  device ? "device_id-found" : undefined,
                  errors.device_id && "device_id-error",
                )}
                className="h-11 font-mono sm:max-w-xs"
              />
              {device ? (
                <p id="device_id-found" className="type-body text-foreground">
                  Dotyczy: <strong className="font-semibold">{deviceName ?? device.id}</strong>
                  {deviceAddress ? <span className="text-muted-foreground"> · {deviceAddress}</span> : null}
                </p>
              ) : null}
              <ErrorText id="device_id-error">{errors.device_id}</ErrorText>
            </div>

            <fieldset aria-describedby={describedBy("location-hint", errors.location && "location-error")} className="flex flex-col gap-2">
              <legend className="type-h4 mb-2 text-foreground">
                Miejsce <span className="type-body font-normal text-muted-foreground">(nieobowiązkowe)</span>
              </legend>
              <p id="location-hint" className="type-caption text-muted-foreground">
                Najważniejsze przy brakującym AED i złym położeniu. Stań przy urządzeniu i użyj lokalizacji telefonu
                albo wpisz współrzędne z mapy, np. 52.2297 i 21.0122.
              </p>
              <div>
                <Button type="button" variant="outline" size="lg" onClick={fillMyLocation} disabled={locate.busy}>
                  {locate.busy ? <Spinner data-icon="inline-start" /> : <LocateFixedIcon data-icon="inline-start" aria-hidden />}
                  Użyj mojej lokalizacji
                </Button>
              </div>
              <p className="type-caption min-h-5 text-muted-foreground" aria-live="polite">
                {locate.text}
              </p>
              <ErrorText id="location-error">{errors.location}</ErrorText>
              <div className="grid grid-cols-2 gap-3 sm:max-w-md">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="lat" className="type-body font-medium text-foreground">
                    Szerokość
                  </label>
                  <Input
                    id="lat"
                    name="lat"
                    inputMode="decimal"
                    autoComplete="off"
                    value={lat}
                    onChange={(e) => {
                      setLat(e.target.value);
                      setErrors((er) => ({ ...er, location: undefined }));
                    }}
                    aria-invalid={errors.location ? true : undefined}
                    aria-describedby={describedBy(errors.location && "location-error")}
                    className="h-11 font-mono"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="lon" className="type-body font-medium text-foreground">
                    Długość
                  </label>
                  <Input
                    id="lon"
                    name="lon"
                    inputMode="decimal"
                    autoComplete="off"
                    value={lon}
                    onChange={(e) => {
                      setLon(e.target.value);
                      setErrors((er) => ({ ...er, location: undefined }));
                    }}
                    aria-invalid={errors.location ? true : undefined}
                    aria-describedby={describedBy(errors.location && "location-error")}
                    className="h-11 font-mono"
                  />
                </div>
              </div>
            </fieldset>

            <div className="flex flex-col gap-2">
              <label htmlFor="description" className="type-h4 text-foreground">
                Opis <span className="type-body font-normal text-muted-foreground">(wymagany)</span>
              </label>
              <p id="description-hint" className="type-caption text-muted-foreground">
                {kind ? DESCRIPTION_HINT[kind] : "Co się nie zgadza i jak jest naprawdę."}
              </p>
              <Textarea
                id="description"
                name="description"
                rows={5}
                maxLength={MAX}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setErrors((er) => ({ ...er, description: undefined }));
                }}
                aria-invalid={errors.description ? true : undefined}
                aria-describedby={describedBy("description-hint", "description-count", errors.description && "description-error")}
                className="min-h-32"
              />
              <p id="description-count" className="type-caption text-subtle-foreground">
                {description.length} z {MAX} znaków
              </p>
              <ErrorText id="description-error">{errors.description}</ErrorText>
            </div>

            <div className="flex flex-col gap-2">
              <label htmlFor="contact_email" className="type-h4 text-foreground">
                Twój e-mail <span className="type-body font-normal text-muted-foreground">(nieobowiązkowy)</span>
              </label>
              <p id="contact_email-hint" className="type-caption text-muted-foreground">
                Użyjemy go tylko, żeby dopytać o szczegóły zgłoszenia. Nigdy go nie publikujemy ani nie przekazujemy
                dalej.
              </p>
              <Input
                id="contact_email"
                name="contact_email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setErrors((er) => ({ ...er, contact_email: undefined }));
                }}
                aria-invalid={errors.contact_email ? true : undefined}
                aria-describedby={describedBy("contact_email-hint", errors.contact_email && "contact_email-error")}
                className="h-11 sm:max-w-md"
              />
              <ErrorText id="contact_email-error">{errors.contact_email}</ErrorText>
            </div>

            {/* Honeypot: invisible and unreachable for people, filled in by bots; the server drops such reports */}
            <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
              <label htmlFor="website">Strona internetowa (zostaw puste)</label>
              <input
                id="website"
                name="website"
                type="text"
                tabIndex={-1}
                autoComplete="off"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center">
              <Button type="submit" variant="cta" size="lg" disabled={state === "sending"} className="sm:min-w-56">
                {state === "sending" ? <Spinner data-icon="inline-start" /> : <SendIcon data-icon="inline-start" aria-hidden />}
                {state === "sending" ? "Wysyłam…" : "Wyślij zgłoszenie"}
              </Button>
              <p className="type-caption text-muted-foreground">
                Zgłoszenia czyta opiekun zbioru. Nie publikujemy ich.
              </p>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
