/** Plain-language Polish descriptions of an AED for the public page. Unknown is said out loud, never implied away. */

import type { NearbyAed } from "@/lib/api";
import { openingState, type Moment, type OpenState } from "@/lib/opening-hours";

const WEEKDAY = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."];

export type Tone = "positive" | "caution" | "negative" | "neutral";

export type Availability = { tone: Tone; headline: string; detail: string | null; open: OpenState };

function when(m: Moment) {
  const time = m.time === "00:00" ? "północy" : m.time;
  if (m.day === 0) return m.time === "00:00" ? "dziś o północy" : `dziś o ${time}`;
  if (m.day === 1) return m.time === "00:00" ? "o północy" : `jutro o ${time}`;
  return `${WEEKDAY[m.weekday]} o ${time}`;
}

function until(m: Moment) {
  if (m.time === "00:00" && m.day === 1) return "do północy";
  if (m.day === 0) return `do ${m.time}`;
  return m.day === 1 ? `do jutra, ${m.time}` : `do ${WEEKDAY[m.weekday]} ${m.time}`;
}

/** Can I get to it right now? From opening_hours, the access level and the device's own placement. */
export function availability(aed: NearbyAed["aed"], now = new Date()): Availability {
  const open = openingState(aed.opening_hours, now);
  const outdoor = aed.placement === "outside_on_building" || aed.placement === "freestanding_outdoor";
  if (open.state === "open") {
    return {
      tone: "positive",
      headline: open.allDay ? "Otwarte całą dobę" : "Otwarte teraz",
      detail: open.allDay ? null : open.until ? `według godzin otwarcia, ${until(open.until)}` : null,
      open,
    };
  }
  if (open.state === "closed") {
    return {
      tone: "negative",
      headline: "Teraz zamknięte",
      detail: open.next ? `według godzin otwarcia; otwarcie ${when(open.next)}` : "według godzin otwarcia",
      open,
    };
  }
  if (open.reason === "none") {
    return {
      tone: "neutral",
      headline: "Brak danych o godzinach",
      detail: outdoor
        ? "Urządzenie jest na zewnątrz, ale nie wiemy, czy szafka jest otwarta"
        : "Nie wiemy, czy miejsce jest teraz otwarte — sprawdź na miejscu",
      open,
    };
  }
  return {
    tone: "neutral",
    headline: "Nie wiemy, czy teraz otwarte",
    detail: "Godziny są opisane w sposób, którego nie umiemy ocenić — zobacz poniżej",
    open,
  };
}

export const ACCESS_TEXT: Record<string, string> = {
  public: "Ogólnodostępny",
  limited: "Dostęp ograniczony (np. tylko dla klientów lub w godzinach pracy)",
  private: "Prywatny — może nie być dostępny dla osób z zewnątrz",
  unknown: "Brak danych o dostępie",
};

export const READINESS_TEXT: Record<string, { tone: Tone; label: string; detail: string }> = {
  ready: { tone: "positive", label: "Sprawny", detail: "Elektrody, bateria i przegląd w terminie według danych." },
  attention: {
    tone: "caution",
    label: "Wymaga uwagi",
    detail: "Zbliża się termin wymiany elektrod, baterii albo przeglądu.",
  },
  expired: {
    tone: "negative",
    label: "Po terminie",
    detail: "Elektrody, bateria albo przegląd są po terminie. Jeśli inny AED jest równie blisko, wybierz go.",
  },
  unknown: {
    tone: "neutral",
    label: "Brak danych o sprawności",
    detail: "Nikt nie przekazał dat przeglądu ani wymiany elektrod.",
  },
};

export function floorText(floor: string | null) {
  if (floor === null || floor === "") return null;
  const n = Number(floor.replace(",", "."));
  if (Number.isNaN(n)) return `piętro: ${floor}`;
  if (n === 0) return "parter";
  return n < 0 ? `poziom ${n} (pod ziemią)` : `${n}. piętro`;
}

/** Place in the building and floor, without repeating the floor when the description already says it. */
export function whereText(aed: { location_detail: string | null; floor: string | null }) {
  const detail = aed.location_detail?.trim() || null;
  const floor = floorText(aed.floor);
  if (detail && floor && detail.toLowerCase().includes(floor.toLowerCase())) return detail;
  return [detail, floor].filter(Boolean).join(" · ");
}

/** Straight-line distance → a walking estimate: routes run ~30% longer than the crow flies, at ~4.8 km/h. */
export function walkingMinutes(distanceM: number) {
  return Math.max(1, Math.ceil((distanceM * 1.3) / 80));
}

/** Beyond this a walking time means nothing in an emergency: say only the distance. */
export const FAR_M = 3000;

/** "ok. 4 min pieszo", "ok. 1 h 5 min pieszo", or null when it is too far to walk. */
export function walkingText(distanceM: number) {
  if (distanceM > FAR_M) return null;
  const min = walkingMinutes(distanceM);
  return min < 60 ? `ok. ${min} min pieszo` : `ok. ${Math.floor(min / 60)} h ${min % 60} min pieszo`;
}

/** "107 m w linii prostej · ok. 2 min pieszo" */
export function distanceLine(distanceM: number) {
  const walk = walkingText(distanceM);
  return walk ? `w linii prostej · ${walk}` : "w linii prostej — za daleko, by dojść pieszo";
}

export function distanceText(m: number) {
  return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1).replace(".", ",")} km`;
}

export function title(aed: NearbyAed["aed"]) {
  return aed.building_name || aed.address || (aed.city ? `Defibrylator AED, ${aed.city}` : "Defibrylator AED");
}

/** geo: URI for the phone's own map app (Android and most mobile browsers). */
export function geoUri(aed: NearbyAed["aed"]) {
  return `geo:${aed.lat},${aed.lon}?q=${aed.lat},${aed.lon}(AED)`;
}

export function osmDirections(aed: NearbyAed["aed"], from: { lat: number; lon: number }) {
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route=${from.lat}%2C${from.lon}%3B${aed.lat}%2C${aed.lon}`;
}
