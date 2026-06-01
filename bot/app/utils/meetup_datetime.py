import re
from datetime import UTC, datetime

MEETUP_DATETIME_FORMAT = "%d.%m.%Y %H:%M"
MEETUP_DATETIME_EXAMPLE = "15.06 19:30"

_INPUT_DATETIME_PATTERN = re.compile(
    r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2})(?:\.(?P<year>\d{2}|\d{4}))?\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})$"
)


def parse_meetup_datetime(value: str, *, now: datetime | None = None) -> datetime | None:
    text = value.strip()
    match = _INPUT_DATETIME_PATTERN.fullmatch(text)
    if match is None:
        return None

    current_year = _get_current_year(now)
    raw_year = match.group("year")
    if raw_year is None:
        year = current_year
    elif len(raw_year) == 2:
        year = _expand_two_digit_year(int(raw_year), current_year)
    else:
        year = int(raw_year)

    try:
        return datetime(
            year,
            int(match.group("month")),
            int(match.group("day")),
            int(match.group("hour")),
            int(match.group("minute")),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def is_future_meetup_datetime(value: datetime, *, now: datetime | None = None) -> bool:
    reference = now or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)
    return value > reference


WEEKDAY_NAMES = [
    "в понедельник",
    "во вторник",
    "в среду",
    "в четверг",
    "в пятницу",
    "в субботу",
    "в воскресенье",
]


def format_meetup_datetime(value: str) -> str:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)
    return parsed.strftime(MEETUP_DATETIME_FORMAT)


def format_meetup_weekday_time(value: str) -> str:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)
    weekday = WEEKDAY_NAMES[parsed.weekday()]
    time_label = parsed.strftime("%H:%M")
    return f"{weekday} в {time_label}"


def _get_current_year(now: datetime | None) -> int:
    if now is None:
        return datetime.now(UTC).year
    if now.tzinfo is None:
        return now.year
    return now.astimezone(UTC).year


def _expand_two_digit_year(parsed_year: int, current_year: int) -> int:
    return (current_year // 100 * 100) + (parsed_year % 100)
