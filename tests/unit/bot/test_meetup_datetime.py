from datetime import UTC, datetime

from bot.app.utils.meetup_datetime import format_meetup_datetime, parse_meetup_datetime


def test_parse_meetup_datetime_accepts_expected_format() -> None:
    parsed = parse_meetup_datetime("15.06.2026 19:30")
    assert parsed == datetime(2026, 6, 15, 19, 30, tzinfo=UTC)


def test_parse_meetup_datetime_rejects_invalid_format() -> None:
    assert parse_meetup_datetime("2026-06-15 19:30") is None


def test_format_meetup_datetime_from_iso_string() -> None:
    assert format_meetup_datetime("2026-06-15T19:30:00+00:00") == "15.06.2026 19:30"
