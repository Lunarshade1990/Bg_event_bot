from datetime import UTC, datetime

from bot.app.utils.meetup_datetime import (
    format_meetup_datetime,
    is_future_meetup_datetime,
    parse_meetup_datetime,
)


def test_parse_meetup_datetime_accepts_expected_format() -> None:
    parsed = parse_meetup_datetime("15.06.2026 19:30")
    assert parsed == datetime(2026, 6, 15, 19, 30, tzinfo=UTC)


def test_parse_meetup_datetime_accepts_two_digit_year() -> None:
    parsed = parse_meetup_datetime("15.06.27 19:30")
    assert parsed == datetime(2027, 6, 15, 19, 30, tzinfo=UTC)


def test_parse_meetup_datetime_expands_two_digit_year_in_current_century() -> None:
    parsed = parse_meetup_datetime(
        "15.06.99 19:30",
        now=datetime(2026, 6, 15, 12, 0, tzinfo=UTC),
    )
    assert parsed == datetime(2099, 6, 15, 19, 30, tzinfo=UTC)


def test_parse_meetup_datetime_uses_current_year_when_year_is_missing() -> None:
    parsed = parse_meetup_datetime(
        "15.06 19:30",
        now=datetime(2028, 12, 30, 12, 0, tzinfo=UTC),
    )
    assert parsed == datetime(2028, 6, 15, 19, 30, tzinfo=UTC)


def test_parse_meetup_datetime_rejects_invalid_format() -> None:
    assert parse_meetup_datetime("2026-06-15 19:30") is None


def test_format_meetup_datetime_from_iso_string() -> None:
    assert format_meetup_datetime("2026-06-15T19:30:00+00:00") == "15.06.2026 19:30"


def test_is_future_meetup_datetime_checks_against_current_time() -> None:
    now = datetime(2026, 6, 15, 19, 30, tzinfo=UTC)

    assert is_future_meetup_datetime(datetime(2026, 6, 15, 19, 31, tzinfo=UTC), now=now)
    assert not is_future_meetup_datetime(
        datetime(2026, 6, 15, 19, 30, tzinfo=UTC),
        now=now,
    )
