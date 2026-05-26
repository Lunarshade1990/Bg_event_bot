from datetime import UTC, datetime

MEETUP_DATETIME_FORMAT = "%d.%m.%Y %H:%M"
MEETUP_DATETIME_EXAMPLE = "15.06.2026 19:30"


def parse_meetup_datetime(value: str) -> datetime | None:
    text = value.strip()
    try:
        parsed = datetime.strptime(text, MEETUP_DATETIME_FORMAT)
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


def format_meetup_datetime(value: str) -> str:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)
    return parsed.strftime(MEETUP_DATETIME_FORMAT)
