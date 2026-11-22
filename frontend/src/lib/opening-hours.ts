/**
 * Human-readable OSM `opening_hours` (https://wiki.openstreetmap.org/wiki/Key:opening_hours).
 *
 * Covers the subset that occurs in our data: month/date ranges, weekday lists, PH/SH, time spans, `24/7`,
 * `off`/`closed` and quoted comments. Anything outside that subset returns `null`, so the caller shows the
 * source value instead of a guess.
 */

export type OpeningHoursLocale = "pl" | "en";

/** One rule: when it applies and what the AED availability is then. */
export type OpeningHoursLine = { when: string | null; what: string };

type Dict = {
  days: Record<string, string>;
  months: string[];
  everyDay: string;
  allYear: string;
  alwaysOpen: string;
  allDay: string;
  closed: string;
  open: string;
  nextDay: string;
  openEnd: (from: string) => string;
  orLonger: string;
  dayMonth: (day: number, month: string) => string;
};

const DICT: Record<OpeningHoursLocale, Dict> = {
  pl: {
    days: {
      Mo: "pon.",
      Tu: "wt.",
      We: "śr.",
      Th: "czw.",
      Fr: "pt.",
      Sa: "sob.",
      Su: "niedz.",
      PH: "święta",
      SH: "ferie szkolne",
    },
    months: ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
    everyDay: "codziennie",
    allYear: "cały rok",
    alwaysOpen: "całodobowo, 7 dni w tygodniu",
    allDay: "całą dobę",
    closed: "niedostępny",
    open: "dostępny",
    nextDay: "do następnego dnia",
    openEnd: (from) => `od ${from} (koniec nieokreślony)`,
    orLonger: "lub dłużej",
    dayMonth: (day, month) => `${day} ${month}`,
  },
  en: {
    days: {
      Mo: "Mon",
      Tu: "Tue",
      We: "Wed",
      Th: "Thu",
      Fr: "Fri",
      Sa: "Sat",
      Su: "Sun",
      PH: "public holidays",
      SH: "school holidays",
    },
    months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    everyDay: "daily",
    allYear: "all year",
    alwaysOpen: "24 hours, 7 days a week",
    allDay: "24 hours",
    closed: "unavailable",
    open: "available",
    nextDay: "until the next day",
    openEnd: (from) => `from ${from} (no fixed end)`,
    orLonger: "or later",
    dayMonth: (day, month) => `${month} ${day}`,
  },
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MON = `(?:${MONTHS.join("|")})`;
const MONTH_POINT = `${MON}(?:\\s+\\d{1,2}(?![\\d:]))?`;
const MONTH_ITEM = `${MONTH_POINT}(?:\\s*-\\s*${MONTH_POINT})?`;
const MONTH_SEL = new RegExp(`^(${MONTH_ITEM}(?:\\s*,\\s*${MONTH_ITEM})*)(?:\\s*:)?\\s*`);

const DAY = "(?:Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)";
const DAY_ITEM = `${DAY}(?:\\s*-\\s*${DAY})?`;
// Items joined by "," (a list) or by a space ("SH Mo-Fr": weekdays within school holidays)
const DAY_SEL = new RegExp(`^(${DAY_ITEM}(?:(?:\\s*,\\s*|\\s+)${DAY_ITEM})*)(?:\\s*:)?(?=\\s|$|")\\s*`);

const TIME = "\\d{1,2}:\\d{2}";
const SPAN = `${TIME}(?:\\s*-\\s*${TIME}\\+?|\\+)`;
const SPANS = new RegExp(`^(${SPAN}(?:\\s*,\\s*${SPAN})*)\\s*`);
const STATE = /^(24\/7|off|closed|open)\b\s*/i;
const COMMENT = /^"([^"]*)"\s*/;
const SEPARATOR = /^(?:;|,|\|\|)\s*/;

function pad(time: string) {
  const [h, m] = time.split(":");
  return `${h.padStart(2, "0")}:${m}`;
}

function minutes(time: string) {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

function formatMonths(sel: string, d: Dict) {
  const items = sel.split(/\s*,\s*/);
  if (items.length === 1 && /^Jan\s*-\s*Dec$/.test(items[0])) return d.allYear;
  const point = (p: string) => {
    const [mon, day] = p.trim().split(/\s+/);
    const name = d.months[MONTHS.indexOf(mon)];
    return day ? d.dayMonth(Number(day), name) : name;
  };
  return items
    .map((item) => {
      const [from, to] = item.split(/\s*-\s*/);
      if (!to) return point(from);
      // A date range reads better with spaces around the dash: "14 kwi – 15 paź"
      const dash = /\d/.test(item) ? " – " : "–";
      return `${point(from)}${dash}${point(to)}`;
    })
    .join(", ");
}

function formatDays(sel: string, d: Dict) {
  // "Mo - Fr" is one range: close up the dash before splitting "SH Mo-Fr" on spaces
  const groups = sel.replace(/\s*-\s*/g, "-").split(/\s*,\s*/).map((group) => group.split(/\s+/));
  const item = (it: string) => {
    const [from, to] = it.split(/\s*-\s*/);
    if (to && from === "Mo" && to === "Su") return d.everyDay;
    return to ? `${d.days[from]}–${d.days[to]}` : d.days[from];
  };
  return groups.map((parts) => parts.map(item).join(" ")).join(", ");
}

function formatSpan(span: string, d: Dict) {
  const openEnd = span.match(new RegExp(`^(${TIME})\\+$`));
  if (openEnd) return d.openEnd(pad(openEnd[1]));
  const [, from, to, plus] = span.match(new RegExp(`^(${TIME})\\s*-\\s*(${TIME})(\\+?)$`))!;
  if (minutes(from) === 0 && minutes(to) === 24 * 60) return d.allDay;
  const text = `${pad(from)}–${pad(to)}`;
  if (plus) return `${text} ${d.orLonger}`;
  // "15:00-07:00" wraps past midnight
  return minutes(to) < minutes(from) ? `${text} (${d.nextDay})` : text;
}

function parseRule(input: string, d: Dict): { line: OpeningHoursLine; rest: string } | null {
  let rest = input;
  const take = (re: RegExp) => {
    const m = rest.match(re);
    if (!m) return null;
    rest = rest.slice(m[0].length);
    return m;
  };

  const months = take(MONTH_SEL);
  const days = take(DAY_SEL);
  const state = take(STATE);
  const spans = state ? null : take(SPANS);
  const comment = take(COMMENT);

  let what: string | null = null;
  if (state) {
    const s = state[1].toLowerCase();
    what = s === "24/7" ? d.alwaysOpen : s === "open" ? d.open : d.closed;
  } else if (spans) {
    what = spans[1]
      .split(/\s*,\s*/)
      .map((s) => formatSpan(s, d))
      .join(", ");
  }
  if (comment) what = what ? `${what} („${comment[1].trim()}”)` : comment[1].trim();
  // A selector with nothing after it would mean "open all day" in OSM, which mappers rarely mean: don't guess
  if (!what) return null;

  const when = [months && formatMonths(months[1], d), days && formatDays(days[1], d)].filter(Boolean).join(", ");
  // Only time spans get an explicit "daily"; "24/7", "closed" or a lone comment read fine on their own
  const timed = spans !== null;
  return {
    line: { when: when || (timed ? d.everyDay : null), what },
    rest,
  };
}

/** Rules in source order, or `null` when the value uses syntax this formatter doesn't know. */
export function parseOpeningHours(value: string, locale: OpeningHoursLocale = "pl"): OpeningHoursLine[] | null {
  const d = DICT[locale];
  const lines: OpeningHoursLine[] = [];
  let rest = value.trim();
  while (rest) {
    const rule = parseRule(rest, d);
    if (!rule || rule.rest === rest) return null;
    lines.push(rule.line);
    rest = rule.rest.replace(SEPARATOR, "").trim();
  }
  return lines.length ? lines : null;
}

// ---------------------------------------------------------------- is it open now?

/**
 * Whether an AED with these `opening_hours` can be reached at a given moment, for the public "nearest AED" page.
 * Same syntax subset as the formatter above. Anything it can't decide (no value, unknown syntax, school holidays,
 * a rule that is only a comment, an open end) is `unknown`: the page then says so instead of implying access.
 */
export type OpenState =
  | { state: "open"; allDay: boolean; until: Moment | null }
  | { state: "closed"; next: Moment | null }
  | { state: "unknown"; reason: "none" | "unparsed" | "uncertain" };

/** A moment relative to now: `day` 0 = today, 1 = tomorrow…; `time` as HH:MM; `weekday` 0 = Monday. */
export type Moment = { day: number; weekday: number; time: string };

type Span = { from: number; to: number | null }; // minutes; `to` > 1440 runs past midnight, null = open end
type Rule = {
  kind: "normal" | "additional" | "fallback";
  months: string | null;
  days: string | null;
  spans: Span[] | null; // null = the rule is only a comment: we can't tell
};
type Day = { y: number; m: number; d: number; weekday: number }; // m 0-11, weekday 0 = Monday

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

function structuredRules(value: string): Rule[] | null {
  const rules: Rule[] = [];
  let rest = value.trim();
  let kind: Rule["kind"] = "normal";
  while (rest) {
    const before = rest;
    const take = (re: RegExp) => {
      const m = rest.match(re);
      if (!m) return null;
      rest = rest.slice(m[0].length);
      return m;
    };
    const months = take(MONTH_SEL);
    const days = take(DAY_SEL);
    const state = take(STATE);
    const spans = state ? null : take(SPANS);
    const comment = take(COMMENT);
    if (!state && !spans && !comment) return null;
    let parsed: Span[] | null = null;
    if (state) {
      const s = state[1].toLowerCase();
      parsed = s === "off" || s === "closed" ? [] : [{ from: 0, to: 24 * 60 }];
    } else if (spans) {
      parsed = spans[1].split(/\s*,\s*/).map((span) => {
        const open = span.match(new RegExp(`^(${TIME})\\+$`));
        if (open) return { from: minutes(open[1]), to: null };
        const [, from, to, plus] = span.match(new RegExp(`^(${TIME})\\s*-\\s*(${TIME})(\\+?)$`))!;
        const a = minutes(from);
        let b = minutes(to);
        if (b <= a) b += 24 * 60;
        return { from: a, to: plus ? null : b };
      });
    }
    rules.push({ kind, months: months?.[1] ?? null, days: days?.[1] ?? null, spans: parsed });
    if (rest === before) return null;
    const sep = rest.match(SEPARATOR);
    kind = !sep ? "normal" : sep[0].startsWith("||") ? "fallback" : sep[0].startsWith(",") ? "additional" : "normal";
    rest = rest.replace(SEPARATOR, "").trim();
  }
  return rules.length ? rules : null;
}

/** Easter Sunday (Gregorian, anonymous algorithm) as [month 0-11, day]. */
function easter(y: number): [number, number] {
  const a = y % 19;
  const b = Math.floor(y / 100);
  const c = y % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  return [month - 1, ((h + l - 7 * m + 114) % 31) + 1];
}

/** Polish public holidays (dni ustawowo wolne od pracy), incl. 24 December since 2025. */
function isPublicHoliday({ y, m, d }: Day) {
  const fixed = ["0-1", "0-6", "4-1", "4-3", "7-15", "10-1", "10-11", "11-25", "11-26"];
  if (y >= 2025) fixed.push("11-24");
  if (fixed.includes(`${m}-${d}`)) return true;
  const [em, ed] = easter(y);
  const base = Date.UTC(y, em, ed);
  const today = Date.UTC(y, m, d);
  // Easter Sunday, Easter Monday, Pentecost (+49), Corpus Christi (+60)
  return [0, 1, 49, 60].some((offset) => base + offset * 86_400_000 === today);
}

function monthMatches(sel: string, { m, d }: Day) {
  const point = (p: string, end: boolean): [number, number] => {
    const [mon, day] = p.trim().split(/\s+/);
    return [MONTHS.indexOf(mon), day ? Number(day) : end ? 31 : 1];
  };
  const v = m * 100 + d;
  return sel.split(/\s*,\s*/).some((item) => {
    const [from, to] = item.split(/\s*-\s*/);
    const [fm, fd] = point(from, false);
    const [tm, td] = to ? point(to, true) : point(from, true);
    const a = fm * 100 + fd;
    const b = tm * 100 + td;
    return a <= b ? v >= a && v <= b : v >= a || v <= b;
  });
}

/** true / false, or null when it depends on school holidays (which we don't know). */
function dayMatches(sel: string, day: Day): boolean | null {
  let uncertain = false;
  const item = (it: string): boolean => {
    const [from, to] = it.split(/\s*-\s*/);
    if (from === "PH") return isPublicHoliday(day);
    if (from === "SH") {
      uncertain = true;
      return false;
    }
    const a = WEEKDAYS.indexOf(from);
    const b = to ? WEEKDAYS.indexOf(to) : a;
    return a <= b ? day.weekday >= a && day.weekday <= b : day.weekday >= a || day.weekday <= b;
  };
  // "Sa-Su, PH": any group; "SH Mo-Fr": every part of a group
  const result = sel
    .replace(/\s*-\s*/g, "-")
    .split(/\s*,\s*/)
    .some((group) => group.split(/\s+/).every(item));
  return uncertain ? null : result;
}

/** The spans for one calendar day, or null when we can't tell. */
function spansFor(rules: Rule[], day: Day): Span[] | null {
  let spans: Span[] = [];
  let matched = false;
  for (const rule of rules) {
    if (rule.kind === "fallback" && matched) continue;
    if (rule.months && !monthMatches(rule.months, day)) continue;
    if (rule.days) {
      const hit = dayMatches(rule.days, day);
      if (hit === null) return null;
      if (!hit) continue;
    }
    if (rule.spans === null) return null;
    spans = rule.kind === "additional" && rule.spans.length ? [...spans, ...rule.spans] : [...rule.spans];
    matched = true;
  }
  return spans;
}

const hhmm = (min: number) => `${String(Math.floor(min / 60) % 24).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;

/** Calendar day and minute in Poland, whatever the device's time zone. */
function warsawNow(now: Date): { day: Day; minute: number } {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Warsaw",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      hourCycle: "h23",
    })
      .formatToParts(now)
      .map((p) => [p.type, p.value]),
  );
  return { day: dayAt(Number(parts.year), Number(parts.month) - 1, Number(parts.day), 0), minute: Number(parts.hour) * 60 + Number(parts.minute) };
}

function dayAt(y: number, m: number, d: number, offset: number): Day {
  const date = new Date(Date.UTC(y, m, d + offset));
  return { y: date.getUTCFullYear(), m: date.getUTCMonth(), d: date.getUTCDate(), weekday: (date.getUTCDay() + 6) % 7 };
}

export function openingState(value: string | null | undefined, now = new Date()): OpenState {
  if (!value?.trim()) return { state: "unknown", reason: "none" };
  const rules = structuredRules(value);
  if (!rules) return { state: "unknown", reason: "unparsed" };
  const { day: today, minute } = warsawNow(now);
  // Yesterday (for spans past midnight) through a week ahead (for the next opening)
  const days: (Span[] | null)[] = [];
  for (let i = -1; i <= 8; i++) days.push(spansFor(rules, dayAt(today.y, today.m, today.d, i)));
  const at = (offset: number) => days[offset + 1];
  if (at(-1) === null || at(0) === null) return { state: "unknown", reason: "uncertain" };

  // Every span as absolute minutes from today's midnight
  const timeline: Span[] = [];
  for (let offset = -1; offset <= 8; offset++) {
    const spans = at(offset);
    if (!spans) break; // beyond an uncertain day we don't look
    for (const s of spans) timeline.push({ from: s.from + offset * 1440, to: s.to === null ? null : s.to + offset * 1440 });
  }
  timeline.sort((a, b) => a.from - b.from);

  const current = timeline.find((s) => s.from <= minute && (s.to === null || minute < s.to));
  if (current) {
    if (current.to === null) return { state: "unknown", reason: "uncertain" };
    // Follow back-to-back spans (24/7, or 00:00-24:00 days in a row)
    let end = current.to;
    for (const s of timeline) if (s.from <= end && s.to !== null && s.to > end && s.from > current.from) end = s.to;
    if (end - minute >= 7 * 1440) return { state: "open", allDay: true, until: null };
    return { state: "open", allDay: false, until: moment(end, today) };
  }
  const next = timeline.find((s) => s.from > minute);
  return { state: "closed", next: next ? moment(next.from, today) : null };
}

function moment(absolute: number, today: Day): Moment {
  const day = Math.floor(absolute / 1440);
  return { day, weekday: (today.weekday + day) % 7, time: hhmm(absolute - day * 1440) };
}
