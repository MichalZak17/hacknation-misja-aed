/**
 * Address → coordinates with Nominatim (OpenStreetMap), falling back to Photon (komoot, same OSM data), within the
 * Nominatim usage policy
 * (https://operations.osmfoundation.org/policies/nominatim/): one request per explicit search (never as-you-type
 * autocomplete), at most one per second from this tab, answers cached in memory, results limited to Poland. The browser
 * identifies the app by its Referer; nothing but the typed text is sent.
 */

export type Place = { label: string; lat: number; lon: number };

const ENDPOINT = "https://nominatim.openstreetmap.org/search";
const MIN_INTERVAL_MS = 1100;

const answers = new Map<string, Place[]>();
let lastRequest = 0;

export class GeocodeError extends Error {}

/**
 * Nominatim finds nothing when the query says "ul." or "ulica" (OSM street names in Poland never include it):
 * "ul. Marszałkowska 10, Warszawa" → no result, "Marszałkowska 10, Warszawa" → found. "al.", "pl." and "os." are
 * understood, so only the street prefix is dropped.
 */
export function normalizeQuery(text: string): string {
  return text
    .replace(/(^|[\s,])(ul\.|ulica(?=[\s,]|$)|ul(?=\s))\s*/giu, "$1")
    .replace(/\s*,\s*/g, ", ")
    .replace(/\s+/g, " ")
    .replace(/^[\s,]+|[\s,]+$/g, "");
}

/**
 * Nominatim first; when it finds nothing (a typo such as "Klemiensiewicza", a flat number such as "6/3") or does not
 * answer, Photon, which matches loosely and knows house numbers from the same OSM data.
 */
export async function geocode(text: string): Promise<Place[]> {
  const q = normalizeQuery(text);
  let failure: unknown = null;
  try {
    const found = await search(q);
    if (found.length) return found;
  } catch (e) {
    failure = e;
  }
  try {
    return await photon(q);
  } catch (e) {
    throw failure ?? e;
  }
}

const PHOTON = "https://photon.komoot.io/api/";
const POLAND_BBOX = "14.07,49.0,24.15,54.84";

type PhotonFeature = {
  geometry: { coordinates: [number, number] };
  properties: Partial<Record<"countrycode" | "name" | "street" | "housenumber" | "postcode" | "city" | "district" | "county", string>>;
};

function photonLabel(p: PhotonFeature["properties"]) {
  const street = [p.street, p.housenumber].filter(Boolean).join(" ");
  const place = [p.postcode, p.city ?? p.district ?? p.county].filter(Boolean).join(" ");
  return [p.name, street, place].filter((part, i, all) => part && all.indexOf(part) === i).join(", ");
}

async function photon(q: string): Promise<Place[]> {
  const key = `photon:${q.toLowerCase()}`;
  const known = answers.get(key);
  if (known) return known;
  const params = new URLSearchParams({ q, limit: "5", bbox: POLAND_BBOX });
  let response: Response;
  try {
    response = await fetch(`${PHOTON}?${params}`, { headers: { Accept: "application/json" }, credentials: "omit" });
  } catch {
    throw new GeocodeError("Wyszukiwarka adresów nie odpowiada. Dotknij mapy albo użyj lokalizacji.");
  }
  if (!response.ok) throw new GeocodeError("Wyszukiwarka adresów nie odpowiada. Dotknij mapy albo użyj lokalizacji.");
  const { features } = (await response.json()) as { features: PhotonFeature[] };
  const places = features
    .filter((f) => f.properties.countrycode === "PL")
    .map((f) => ({ label: photonLabel(f.properties), lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }));
  answers.set(key, places);
  return places;
}

async function search(q: string): Promise<Place[]> {
  const key = q.toLowerCase();
  const known = answers.get(key);
  if (known) return known;

  const wait = lastRequest + MIN_INTERVAL_MS - Date.now();
  if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
  lastRequest = Date.now();

  const params = new URLSearchParams({
    q,
    format: "jsonv2",
    countrycodes: "pl",
    limit: "5",
    "accept-language": "pl",
  });
  let response: Response;
  try {
    response = await fetch(`${ENDPOINT}?${params}`, { headers: { Accept: "application/json" }, credentials: "omit" });
  } catch {
    throw new GeocodeError("Wyszukiwarka adresów nie odpowiada. Dotknij mapy albo użyj lokalizacji.");
  }
  if (!response.ok) {
    throw new GeocodeError(
      response.status === 429
        ? "Za dużo wyszukiwań naraz. Spróbuj za chwilę albo dotknij mapy."
        : "Wyszukiwarka adresów nie odpowiada. Dotknij mapy albo użyj lokalizacji.",
    );
  }
  const rows = (await response.json()) as { display_name: string; lat: string; lon: string }[];
  const places = rows.map((r) => ({ label: r.display_name, lat: Number(r.lat), lon: Number(r.lon) }));
  answers.set(key, places);
  return places;
}
