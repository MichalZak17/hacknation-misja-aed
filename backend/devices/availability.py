"""Is the AED reachable at a given moment? Evaluates a device's OSM `opening_hours` (Europe/Warsaw local time).

The same syntax subset and the same rules as the public page's `openingState` (frontend/src/lib/opening-hours.ts), so
the API and the page never disagree: month/date ranges, weekday lists, PH (Polish public holidays), time spans
(past midnight too), `24/7`, `off`/`closed`/`open`, quoted comments, `;` `,` and `||` rule separators. Whatever it
cannot decide is `unknown` and says why — no value (`none`), syntax outside the subset (`unparsed`), or a rule that
depends on school holidays, is only a comment or has an open end (`uncertain`) — so a client never implies access the
data does not state.

`state` answers only "do the stated hours cover this moment"; whether the public may use the AED at all is `access`.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from django.utils import timezone

WARSAW = ZoneInfo("Europe/Warsaw")
DAY_MINUTES = 24 * 60

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MON = f"(?:{'|'.join(MONTHS)})"
_MONTH_POINT = rf"{_MON}(?:\s+\d{{1,2}}(?![\d:]))?"
_MONTH_ITEM = rf"{_MONTH_POINT}(?:\s*-\s*{_MONTH_POINT})?"
MONTH_SEL = re.compile(rf"({_MONTH_ITEM}(?:\s*,\s*{_MONTH_ITEM})*)(?:\s*:)?\s*")

WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_DAY = "(?:Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)"
_DAY_ITEM = rf"{_DAY}(?:\s*-\s*{_DAY})?"
# Items joined by "," (a list) or by a space ("SH Mo-Fr": weekdays within school holidays)
DAY_SEL = re.compile(rf"({_DAY_ITEM}(?:(?:\s*,\s*|\s+){_DAY_ITEM})*)(?:\s*:)?(?=\s|$|\")\s*")

_TIME = r"\d{1,2}:\d{2}"
_SPAN = rf"{_TIME}(?:\s*-\s*{_TIME}\+?|\+)"
SPANS = re.compile(rf"({_SPAN}(?:\s*,\s*{_SPAN})*)\s*")
OPEN_END = re.compile(rf"({_TIME})\+")
CLOSED_SPAN = re.compile(rf"({_TIME})\s*-\s*({_TIME})(\+?)")
STATE = re.compile(r"(24/7|off|closed|open)\b\s*", re.IGNORECASE)
COMMENT = re.compile(r'"([^"]*)"\s*')
SEPARATOR = re.compile(r"(?:;|,|\|\|)\s*")


@dataclass(frozen=True)
class Span:
    start: int  # minutes from the day's midnight
    end: int | None  # > 1440 runs past midnight; None = open end


@dataclass(frozen=True)
class Rule:
    kind: str  # normal | additional | fallback
    months: str | None
    days: str | None
    spans: tuple[Span, ...] | None  # None = the rule is only a comment: we can't tell


def _minutes(value: str) -> int:
    hours, mins = value.split(":")
    return int(hours) * 60 + int(mins)


def _span(text: str) -> Span:
    if match := OPEN_END.fullmatch(text):
        return Span(_minutes(match[1]), None)
    match = CLOSED_SPAN.fullmatch(text)
    start, end = _minutes(match[1]), _minutes(match[2])
    if end <= start:
        end += DAY_MINUTES
    return Span(start, None if match[3] else end)


@lru_cache(maxsize=4096)
def parse(value: str) -> tuple[Rule, ...] | None:
    """The rules of an opening_hours value, or None when it uses syntax outside the supported subset."""
    rules: list[Rule] = []
    rest, kind = value.strip(), "normal"
    while rest:
        before = rest

        def take(pattern: re.Pattern):
            nonlocal rest
            match = pattern.match(rest)
            if match:
                rest = rest[match.end() :]
            return match

        months, days = take(MONTH_SEL), take(DAY_SEL)
        state = take(STATE)
        spans = None if state else take(SPANS)
        comment = take(COMMENT)
        if not (state or spans or comment):
            return None
        parsed: tuple[Span, ...] | None = None
        if state:
            word = state[1].lower()
            parsed = () if word in ("off", "closed") else (Span(0, DAY_MINUTES),)
        elif spans:
            parsed = tuple(_span(s) for s in re.split(r"\s*,\s*", spans[1]))
        rules.append(Rule(kind, months[1] if months else None, days[1] if days else None, parsed))
        if rest == before:
            return None
        separator = SEPARATOR.match(rest)
        if not separator:
            kind = "normal"
        else:
            kind = {"|": "fallback", ",": "additional"}.get(separator[0][0], "normal")
            rest = rest[separator.end() :]
        rest = rest.strip()
    return tuple(rules) or None


def easter(year: int) -> date:
    """Easter Sunday (Gregorian, anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lv = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lv) // 451
    return date(year, (h + lv - 7 * m + 114) // 31, (h + lv - 7 * m + 114) % 31 + 1)


@lru_cache(maxsize=64)
def public_holidays(year: int) -> frozenset[date]:
    """Polish public holidays (dni ustawowo wolne od pracy), incl. 24 December since 2025."""
    fixed = [(1, 1), (1, 6), (5, 1), (5, 3), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)]
    if year >= 2025:
        fixed.append((12, 24))
    sunday = easter(year)
    movable = [
        sunday + timedelta(days=offset) for offset in (0, 1, 49, 60)
    ]  # Easter, Monday, Pentecost, Corpus Christi
    return frozenset([date(year, m, d) for m, d in fixed] + movable)


def _month_matches(selector: str, day: date) -> bool:
    def point(text: str, end: bool) -> int:
        parts = text.strip().split()
        return MONTHS.index(parts[0]) * 100 + (int(parts[1]) if len(parts) > 1 else 31 if end else 1)

    value = (day.month - 1) * 100 + day.day
    for item in re.split(r"\s*,\s*", selector):
        bounds = re.split(r"\s*-\s*", item)
        start, end = point(bounds[0], False), point(bounds[-1], True)
        if (start <= value <= end) if start <= end else (value >= start or value <= end):
            return True
    return False


def _day_matches(selector: str, day: date) -> bool | None:
    """True / False, or None when it depends on school holidays (which we don't know)."""
    uncertain = False

    def item(text: str) -> bool:
        nonlocal uncertain
        bounds = re.split(r"\s*-\s*", text)
        if bounds[0] == "PH":
            return day in public_holidays(day.year)
        if bounds[0] == "SH":
            uncertain = True
            return False
        start, end = WEEKDAYS.index(bounds[0]), WEEKDAYS.index(bounds[-1])
        weekday = day.weekday()
        return (start <= weekday <= end) if start <= end else (weekday >= start or weekday <= end)

    # "Sa-Su, PH": any group; "SH Mo-Fr": every part of a group
    groups = re.split(r"\s*,\s*", re.sub(r"\s*-\s*", "-", selector))  # "Mo - Fr" is one range
    result = any(all(item(part) for part in group.split()) for group in groups)
    return None if uncertain else result


def spans_for(rules: tuple[Rule, ...], day: date) -> list[Span] | None:
    """The spans for one calendar day, or None when we can't tell."""
    spans: list[Span] = []
    matched = False
    for rule in rules:
        if rule.kind == "fallback" and matched:
            continue
        if rule.months and not _month_matches(rule.months, day):
            continue
        if rule.days:
            hit = _day_matches(rule.days, day)
            if hit is None:
                return None
            if not hit:
                continue
        if rule.spans is None:
            return None
        spans = [*spans, *rule.spans] if rule.kind == "additional" and rule.spans else list(rule.spans)
        matched = True
    return spans


def _local(at: datetime | None) -> datetime:
    at = at or timezone.now()
    if timezone.is_naive(at):
        at = at.replace(tzinfo=WARSAW)
    return at.astimezone(WARSAW).replace(second=0, microsecond=0)


def _moment(today: date, absolute: int) -> str:
    """Minutes from today's local midnight → ISO datetime with the Warsaw offset of that moment."""
    day, minute = divmod(absolute, DAY_MINUTES)
    naive = datetime.combine(today + timedelta(days=day), time(minute // 60, minute % 60))
    return naive.replace(tzinfo=WARSAW).isoformat()


def availability(opening_hours: str | None, at: datetime | None = None) -> dict:
    """{state, open_24_7, until, next_open, reason, checked_at} for `opening_hours` at `at` (default now).

    state      open · closed · unknown
    open_24_7  open with no end within a week (24/7, or every day 00:00-24:00)
    until      when an `open` state ends (ISO datetime, Europe/Warsaw), null for open_24_7
    next_open  when a `closed` state ends, null if not within a week
    reason     why `unknown`: none · unparsed · uncertain; null otherwise
    """
    local = _local(at)
    body = {
        "state": "unknown",
        "open_24_7": False,
        "until": None,
        "next_open": None,
        "reason": None,
        "checked_at": local.isoformat(),
    }
    if not opening_hours or not opening_hours.strip():
        return body | {"reason": "none"}
    rules = parse(opening_hours)
    if not rules:
        return body | {"reason": "unparsed"}
    today, minute = local.date(), local.hour * 60 + local.minute
    # Yesterday (for spans past midnight) through a week ahead (for the next opening)
    days = {offset: spans_for(rules, today + timedelta(days=offset)) for offset in range(-1, 9)}
    if days[-1] is None or days[0] is None:
        return body | {"reason": "uncertain"}

    timeline: list[Span] = []
    for offset in range(-1, 9):
        if days[offset] is None:
            break  # beyond an uncertain day we don't look
        shift = offset * DAY_MINUTES
        timeline += [Span(s.start + shift, None if s.end is None else s.end + shift) for s in days[offset]]
    timeline.sort(key=lambda s: s.start)

    current = next((s for s in timeline if s.start <= minute and (s.end is None or minute < s.end)), None)
    if current:
        if current.end is None:
            return body | {"reason": "uncertain"}
        # Follow back-to-back spans (24/7, or 00:00-24:00 days in a row)
        end = current.end
        for s in timeline:
            if s.start <= end and s.end is not None and s.end > end and s.start > current.start:
                end = s.end
        if end - minute >= 7 * DAY_MINUTES:
            return body | {"state": "open", "open_24_7": True}
        return body | {"state": "open", "until": _moment(today, end)}
    upcoming = next((s for s in timeline if s.start > minute), None)
    return body | {"state": "closed", "next_open": _moment(today, upcoming.start) if upcoming else None}


def is_open(opening_hours: str | None, at: datetime | None = None) -> bool:
    return availability(opening_hours, at)["state"] == "open"
