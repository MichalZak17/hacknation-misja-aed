"""`opening_hours` → open / closed / unknown at a moment (devices/availability.py), Europe/Warsaw local time."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from devices.availability import availability, easter, parse, public_holidays

WARSAW = ZoneInfo("Europe/Warsaw")
MONDAY_10 = datetime(2026, 11, 23, 10, 0, tzinfo=WARSAW)  # an ordinary Monday
SATURDAY_10 = datetime(2026, 11, 21, 10, 0, tzinfo=WARSAW)


def at(value: str, moment: datetime) -> dict:
    return availability(value, moment)


def test_always_open():
    body = at("24/7", MONDAY_10)
    assert body["state"] == "open" and body["open_24_7"] is True and body["until"] is None
    assert at("Mo-Su 00:00-24:00", SATURDAY_10)["open_24_7"] is True


def test_office_hours():
    body = at("Mo-Fr 07:30-15:30; Sa-Su, PH off", MONDAY_10)
    assert body["state"] == "open" and body["until"] == "2026-11-23T15:30:00+01:00"
    weekend = at("Mo-Fr 07:30-15:30; Sa-Su, PH off", SATURDAY_10)
    assert weekend["state"] == "closed" and weekend["next_open"] == "2026-11-23T07:30:00+01:00"
    evening = at("Mo-Fr 07:30-15:30", MONDAY_10.replace(hour=18))
    assert evening["state"] == "closed" and evening["next_open"] == "2026-11-24T07:30:00+01:00"


def test_public_holidays():
    assert easter(2026) == date(2026, 4, 5)
    assert date(2026, 6, 4) in public_holidays(2026)  # Corpus Christi
    assert date(2026, 12, 24) in public_holidays(2026) and date(2024, 12, 24) not in public_holidays(2024)
    independence_day = datetime(2026, 11, 11, 10, 0, tzinfo=WARSAW)  # a Wednesday
    assert at("Mo-Fr 08:00-16:00; PH off", independence_day)["state"] == "closed"
    assert at("Mo-Fr 08:00-16:00", independence_day)["state"] == "open"


def test_spans_past_midnight():
    night = "Mo-Su 18:00-06:00"
    assert at(night, MONDAY_10.replace(hour=2))["state"] == "open"  # from Sunday's span
    assert at(night, MONDAY_10.replace(hour=2))["until"] == "2026-11-23T06:00:00+01:00"
    assert at(night, MONDAY_10)["state"] == "closed"


def test_rule_kinds():
    assert at("Mo-Fr 08:00-12:00, Mo 14:00-18:00", MONDAY_10.replace(hour=15))["state"] == "open"  # additional
    assert at("Mo-Fr 08:00-12:00; Mo 14:00-18:00", MONDAY_10)["state"] == "closed"  # a later rule replaces
    assert at('Mo-Fr 08:00-16:00 || "na telefon"', SATURDAY_10)["reason"] == "uncertain"  # fallback, comment only
    assert at("Jun-Aug Mo-Su 08:00-20:00", MONDAY_10)["state"] == "closed"  # out of season
    assert at("Nov 20-Nov 30 08:00-12:00", MONDAY_10)["state"] == "open"


def test_unknown_when_it_cannot_tell():
    assert at(None, MONDAY_10) | {"checked_at": None} == {
        "state": "unknown",
        "open_24_7": False,
        "until": None,
        "next_open": None,
        "reason": "none",
        "checked_at": None,
    }
    assert at("po uzgodnieniu z portiernią", MONDAY_10)["reason"] == "unparsed"
    assert at("SH Mo-Fr 08:00-12:00", MONDAY_10)["reason"] == "uncertain"  # school holidays
    assert at("Mo-Fr 08:00+", MONDAY_10)["reason"] == "uncertain"  # open end


@pytest.mark.parametrize("value", ["24/7", "Mo-Fr 07:00-15:00; Sa,Su off", "07:30-15:30", "Mo 08:00-17:00; Tu-Fr off"])
def test_common_values_parse(value):
    assert parse(value)


def test_naive_moment_is_warsaw_time():
    assert at("Mo-Fr 09:00-11:00", datetime(2026, 11, 23, 10, 0))["checked_at"] == "2026-11-23T10:00:00+01:00"


def test_spaced_day_range():
    assert at("Mo- Fr 7:00-20:00 Sa 07:00-15:00", MONDAY_10)["state"] == "open"  # seen in OSM data
    assert at("Mo - Fr 08:00-16:00", MONDAY_10)["state"] == "open"
