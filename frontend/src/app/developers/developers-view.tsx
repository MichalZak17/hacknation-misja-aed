"use client";

import Link from "next/link";

import { MetaLabel, SectionHeading } from "@/components/brand";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { ApiPlayground, type ApiParam } from "./_components/api-playground";

/**
 * The public API reference, one block per endpoint: parameters you can edit, the request ready to copy into Postman
 * (Import → Raw text) or code, and a live response. Endpoints and their contract: docs/api.md.
 */

const ACCESS = ["public", "limited", "private", "unknown"];

const LAT: ApiParam = {
  name: "lat",
  type: "number",
  required: true,
  default: "52.2297",
  description: "Twoja szerokość geograficzna, WGS84 (EPSG:4326), od -90 do 90.",
};
const LON: ApiParam = {
  name: "lon",
  type: "number",
  required: true,
  default: "21.0122",
  description: "Twoja długość geograficzna, WGS84 (EPSG:4326), od -180 do 180.",
};
const ACCESS_PARAM: ApiParam = {
  name: "access",
  type: "string",
  placeholder: "public,limited",
  description: "Tylko AED o tej dostępności; kilka wartości po przecinku. Bez parametru: każda dostępność.",
  values: ACCESS,
};
const OPEN_NOW: ApiParam = {
  name: "open_now",
  type: "boolean",
  description:
    "true zostawia tylko AED, których godziny dostępności obejmują tę chwilę (teraz albo at). AED bez godzin albo z godzinami, których nie da się rozstrzygnąć, są pomijane.",
};
const AT: ApiParam = {
  name: "at",
  type: "string",
  placeholder: "2026-11-23T23:00",
  description: "Sprawdź dostępność w innej chwili niż teraz (ISO 8601; bez strefy = czas polski).",
};

const NEAREST_PARAMS: ApiParam[] = [
  LAT,
  LON,
  ACCESS_PARAM,
  {
    name: "max_distance_m",
    type: "number",
    placeholder: "1000",
    description: "Promień wyszukiwania w metrach (do 100 000). Gdy w promieniu nie ma AED, odpowiedź to 404.",
  },
  OPEN_NOW,
  AT,
  {
    name: "demo",
    type: "boolean",
    description:
      "true zwraca urządzenie demonstracyjne AED-PL-DEMO z wypełnionym każdym polem, zamiast prawdziwego AED.",
  },
];

const NEARBY_PARAMS: ApiParam[] = [
  LAT,
  LON,
  { name: "limit", type: "number", default: "3", description: "Ile AED, od najbliższego (1–20, domyślnie 5)." },
  ACCESS_PARAM,
  { name: "max_distance_m", type: "number", placeholder: "1000", description: "Promień wyszukiwania w metrach." },
  OPEN_NOW,
  AT,
];

const RECORD_PARAMS: ApiParam[] = [
  {
    name: "id",
    in: "path",
    type: "string",
    required: true,
    default: "AED-PL-DEMO",
    description: "Identyfikator AED, np. AED-PL-009479. AED-PL-DEMO to urządzenie demonstracyjne.",
  },
  AT,
];

const REGION_PARAMS: ApiParam[] = [
  {
    name: "level",
    type: "enum",
    default: "voivodeship",
    values: ["voivodeship", "municipality"],
    description: "voivodeship: 16 województw; municipality: każda gmina (ok. 2480).",
  },
  {
    name: "voivodeship",
    type: "string",
    placeholder: "12",
    description: "Dwucyfrowy kod TERYT województwa: tylko jednostki w nim (np. 12 = małopolskie).",
  },
];

const DEVICES_PARAMS: ApiParam[] = [
  {
    name: "teryt",
    type: "string",
    default: "1261011",
    description:
      "Początek kodu TERYT: 2 cyfry województwo, 4 powiat, 6–7 gmina (np. 1261011 = Kraków, 1465011 = Warszawa).",
  },
  { name: "city", type: "string", placeholder: "Kraków", description: "Miejscowość (dokładnie, bez wielkości liter)." },
  { name: "q", type: "string", placeholder: "dworzec", description: "Tekst w nazwie, adresie, opisie lokalizacji…" },
  { name: "access", type: "enum", values: ACCESS, description: "Dostępność." },
  {
    name: "placement",
    type: "enum",
    values: ["inside_building", "outside_on_building", "freestanding_outdoor", "vehicle", "unknown"],
    description: "Umiejscowienie.",
  },
  { name: "open_24_7", type: "boolean", description: "true: tylko AED dostępne całodobowo (opening_hours 24/7)." },
  {
    name: "bbox",
    type: "string",
    placeholder: "19.9,50.0,20.1,50.1",
    description: "Prostokąt: minLon,minLat,maxLon,maxLat (WGS84).",
  },
  {
    name: "updated_since",
    type: "string",
    placeholder: "2026-11-21T00:00:00Z",
    description: "Tylko AED zmienione po tej chwili (ISO 8601).",
  },
  { name: "limit", type: "number", default: "5", description: "Ile na stronę (do 500)." },
  { name: "offset", type: "number", placeholder: "0", description: "Przesunięcie, do stronicowania." },
];

const CHANGES_PARAMS: ApiParam[] = [
  {
    name: "since",
    type: "string",
    required: true,
    default: "2026-11-21T00:00:00Z",
    description: "Zmiany po tej chwili (ISO 8601). W kolejnym zapytaniu podaj as_of z poprzedniej odpowiedzi.",
  },
  { name: "limit", type: "number", default: "3", description: "Ile zmian na stronę (1–1000, domyślnie 500)." },
  { name: "offset", type: "number", placeholder: "0", description: "Przesunięcie, do stronicowania." },
];

const RESPONSES = [
  { code: "200", meaning: "Znaleziono AED.", body: "NearestAed" },
  { code: "301", meaning: "/api/aed/{id}: AED scalono z innym; Location wskazuje rekord, który został.", body: "" },
  {
    code: "400",
    meaning: "Nieznana wartość parametru (access, level, placement…) albo zły kod TERYT.",
    body: "{ detail }",
  },
  {
    code: "404",
    meaning: "Brak AED w promieniu max_distance_m (albo żadnego otwartego przy open_now), albo nieznany id.",
    body: "{ detail }",
  },
  { code: "410", meaning: "/api/aed/{id}: żadne źródło nie podaje już tego AED.", body: "{ detail }" },
  { code: "422", meaning: "Brak wymaganego parametru, wartość spoza zakresu albo zły typ.", body: "{ detail: [...] }" },
];

const FIELDS = [
  { field: "demo", type: "boolean", note: "true tylko dla urządzenia demonstracyjnego (demo=true)." },
  { field: "query", type: "{ lat, lon }", note: "Punkt, od którego liczono odległość." },
  { field: "distance_m", type: "number", note: "Odległość w linii prostej, w metrach (geodezyjna, WGS84)." },
  {
    field: "aed",
    type: "object",
    note: "Pełny rekord AED: każde pole wzorcowego zakresu danych (jak w eksportach), plus municipality i updated_at. null = źródło tego nie podaje.",
  },
  { field: "availability", type: "object", note: "Czy godziny dostępności obejmują tę chwilę; pola niżej." },
  { field: "links.self", type: "url | null", note: "Szczegóły urządzenia z pochodzeniem każdego pola (null dla demo)." },
  { field: "links.record", type: "url", note: "Rekord AED pod stałym adresem /api/aed/{id}." },
  { field: "links.map", type: "url", note: "Urządzenie na mapie OpenStreetMap." },
  {
    field: "links.directions",
    type: "url",
    note: "Trasa piesza do AED w Mapach Google: od punktu zapytania, a w /api/aed/{id} od miejsca, w którym jest użytkownik.",
  },
];

const AVAILABILITY_FIELDS = [
  {
    field: "state",
    type: "open | closed | unknown",
    note: "open: godziny obejmują tę chwilę; closed: nie obejmują; unknown: nie da się tego rozstrzygnąć.",
  },
  { field: "open_24_7", type: "boolean", note: "Dostępny bez przerwy przez najbliższy tydzień (24/7)." },
  { field: "until", type: "datetime | null", note: "Do kiedy jest dostępny (gdy open i nie 24/7)." },
  { field: "next_open", type: "datetime | null", note: "Od kiedy znów będzie dostępny (gdy closed, w ciągu tygodnia)." },
  {
    field: "reason",
    type: "none | unparsed | uncertain | null",
    note: "Dlaczego unknown: brak godzin, zapis nieczytelny, albo zależy od ferii, komentarza lub otwartego końca.",
  },
  { field: "checked_at", type: "datetime", note: "Sprawdzana chwila (teraz albo at), czas polski." },
];

const SECTIONS = [
  { id: "najblizszy-aed", label: "Najbliższy AED", method: "GET" },
  { id: "kilka-najblizszych", label: "Kilka najbliższych", method: "GET" },
  { id: "jeden-aed", label: "Jeden AED", method: "GET" },
  { id: "dostepnosc", label: "Dostępność teraz" },
  { id: "regiony", label: "AED w regionach", method: "GET" },
  { id: "lista", label: "Lista z filtrami", method: "GET" },
  { id: "zmiany", label: "Zmiany od daty", method: "GET" },
  { id: "kody-odpowiedzi", label: "Kody odpowiedzi" },
  { id: "pola-odpowiedzi", label: "Pola odpowiedzi" },
  { id: "pliki", label: "Pliki i OpenAPI" },
];

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="type-h2 mt-12 scroll-mt-20 border-t border-border pt-6 text-hn-heading">
      <a href={`#${id}`} className="outline-none hover:underline focus-visible:outline-2 focus-visible:outline-ring">
        {children}
      </a>
    </h2>
  );
}

const lead = "type-lead my-4 max-w-[72ch]";
const body = "type-body my-3 max-w-[72ch] text-muted-foreground";

function FieldTable({
  caption,
  rows,
}: {
  caption: string;
  rows: { field: string; type: string; note: string }[];
}) {
  return (
    <div className="my-6">
      <Table>
        <caption className="sr-only">{caption}</caption>
        <TableHeader>
          <TableRow>
            <TableHead>Pole</TableHead>
            <TableHead>Typ</TableHead>
            <TableHead>Opis</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((f) => (
            <TableRow key={f.field}>
              <TableCell>
                <code className="type-code">{f.field}</code>
              </TableCell>
              <TableCell>
                <code className="type-code">{f.type}</code>
              </TableCell>
              <TableCell className="min-w-64 whitespace-normal">{f.note}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function DevelopersView() {
  return (
    <div className="grid gap-6 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-10">
      <nav aria-label="Spis API" className="hidden lg:sticky lg:top-20 lg:block lg:self-start">
        <h2 className="type-label mb-2 px-3 text-subtle-foreground">API</h2>
        <ul className="border-l border-border">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className="type-body flex items-center gap-2 px-3 py-1.5 text-muted-foreground outline-none hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
              >
                {s.method ? <span className="type-micro font-mono font-semibold text-positive">{s.method}</span> : null}
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <article className="min-w-0 bg-background px-5 py-6 ring-1 ring-border md:px-8 md:py-8">
        <MetaLabel prompt>API · dla deweloperów</MetaLabel>
        <SectionHeading as="h1" className="mt-2">
          API Misji AED
        </SectionHeading>
        <p className={lead}>
          Otwarte, bez klucza i logowania. Odpowiada na trzy pytania ratownika: gdzie jest najbliższy AED, czy można z
          niego skorzystać teraz i czy działa. Odpowiedzi są w JSON, współrzędne w WGS84, a <code>null</code> znaczy
          „źródło tego nie podaje”.
        </p>

        <H2 id="najblizszy-aed">Najbliższy AED</H2>
        <p className={lead}>
          Najbliższy AED, z którego da się skorzystać. Pomija AED w pojazdach oraz niesprawne, zaginione i wycofane.
        </p>
        <ApiPlayground
          path="/api/aed/nearest"
          params={NEAREST_PARAMS}
          example={{ demo: "true" }}
          exampleLabel="Przykładowa odpowiedź (urządzenie demo)"
        />

        <H2 id="kilka-najblizszych">Kilka najbliższych AED</H2>
        <p className={lead}>
          Do 20 najbliższych AED, od najbliższego, każdy z pełnym rekordem, dostępnością i linkami. Te same zasady
          pomijania co wyżej. Z tego korzysta strona główna.
        </p>
        <ApiPlayground path="/api/aed/nearby" params={NEARBY_PARAMS} />

        <H2 id="jeden-aed">Jeden AED</H2>
        <p className={lead}>
          Rekord jednego AED pod stałym adresem, do linkowania z innych aplikacji. Gdy dwa rekordy okazały się tym samym
          urządzeniem, stary adres przekierowuje (301) na ten, który został. AED, którego nie podaje już żadne źródło,
          odpowiada 410.
        </p>
        <ApiPlayground path="/api/aed/{id}" params={RECORD_PARAMS} />

        <H2 id="dostepnosc">Dostępność teraz</H2>
        <p className={lead}>
          Każda odpowiedź z AED ma obiekt <code>availability</code>: czy godziny dostępności (
          <code>opening_hours</code>, składnia OpenStreetMap) obejmują tę chwilę.
        </p>
        <p className={body}>
          Liczymy według zegara w Polsce, z polskimi dniami ustawowo wolnymi od pracy (<code>PH</code>). Gdy zapisu nie
          da się rozstrzygnąć, odpowiedź to <code>unknown</code> z powodem, nigdy zgadywanie. Strona główna liczy
          dostępność tą samą regułą, więc strona i API zawsze się zgadzają. <code>state</code> mówi tylko o godzinach;
          czy z AED może skorzystać każdy, mówi pole <code>access</code>.
        </p>
        <FieldTable caption="Pola obiektu availability" rows={AVAILABILITY_FIELDS} />

        <H2 id="regiony">AED w regionach</H2>
        <p className={lead}>
          Liczba AED w każdym województwie albo gminie: według dostępności, całodobowe, zweryfikowane, z powierzchnią z
          granic PRG i liczbą AED na 100 km². Gminy bez żadnego AED też są na liście (<code>devices: 0</code>), więc
          widać białe plamy.
        </p>
        <ApiPlayground path="/api/stats/regions" params={REGION_PARAMS} />

        <H2 id="lista">Lista z filtrami</H2>
        <p className={lead}>
          Lista AED do przeglądania i stronicowania: po gminie, powiecie lub województwie (kod TERYT), miejscowości,
          tekście, dostępności, umiejscowieniu, dostępności całodobowej albo dacie zmiany.
        </p>
        <ApiPlayground path="/api/devices" params={DEVICES_PARAMS} />

        <H2 id="zmiany">Zmiany od daty</H2>
        <p className={lead}>
          Do utrzymywania własnej kopii zbioru bez pobierania całości: AED zmienione po podanej chwili, od najstarszej
          zmiany. <code>updated</code> zawiera aktualny rekord, <code>removed</code> znaczy, że żadne źródło go już nie
          podaje, a <code>merged</code>, że był duplikatem rekordu <code>merged_into</code>.
        </p>
        <p className={body}>
          Pobierz raz pełny plik <a href="/api/export/aeds.json" className="underline">aeds.json</a>, a potem pytaj o
          zmiany, podając jako <code>since</code> wartość <code>as_of</code> z poprzedniej odpowiedzi. Stronicuj przez{" "}
          <code>offset</code>, aż pobierzesz <code>count</code> zmian.
        </p>
        <ApiPlayground path="/api/changes" params={CHANGES_PARAMS} />

        <H2 id="kody-odpowiedzi">Kody odpowiedzi</H2>
        <div className="my-6">
          <Table>
            <caption className="sr-only">Kody odpowiedzi API</caption>
            <TableHeader>
              <TableRow>
                <TableHead>Kod</TableHead>
                <TableHead>Kiedy</TableHead>
                <TableHead>Treść</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {RESPONSES.map((r) => (
                <TableRow key={r.code}>
                  <TableCell>
                    <code className="type-code font-semibold">{r.code}</code>
                  </TableCell>
                  <TableCell className="whitespace-normal">{r.meaning}</TableCell>
                  <TableCell>{r.body ? <code className="type-code">{r.body}</code> : null}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <H2 id="pola-odpowiedzi">Pola odpowiedzi</H2>
        <p className={body}>
          <code>/api/aed/nearest</code>; w <code>/api/aed/nearby</code> te same pola są w każdym elemencie{" "}
          <code>items</code>, a <code>/api/aed/{"{id}"}</code> nie ma <code>query</code> ani <code>distance_m</code>.
          Znaczenie każdego pola rekordu opisuje <Link href="/docs/slownik-danych" className="underline">
            słownik danych
          </Link>.
        </p>
        <FieldTable caption="Pola odpowiedzi NearestAed" rows={FIELDS} />

        <H2 id="pliki">Pliki i OpenAPI</H2>
        <p className={body}>
          Cały zbiór w CSV, GeoJSON, JSON i JSON-LD jest na stronie <Link href="/export" className="underline">
            Dane do pobrania
          </Link>, a definicje pól pod <code>/api/schema</code>. Pełny opis wszystkich publicznych końcówek w
          formacie OpenAPI, z możliwością wywołania: <a href="/api/docs" className="underline">/api/docs</a>.
        </p>
      </article>
    </div>
  );
}
