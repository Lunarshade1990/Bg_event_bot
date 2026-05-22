from enum import StrEnum


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_cls]


class GameType(StrEnum):
    BASE = "base"
    EXPANSION = "expansion"


class CampaignSource(StrEnum):
    UNKNOWN = "unknown"
    BGG = "bgg"
    ADMIN_MANUAL = "admin_manual"


class OwnershipSource(StrEnum):
    BGG_IMPORT = "bgg_import"
    MANUAL = "manual"


class MeetupStatus(StrEnum):
    PLANNED = "planned"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ParticipantStatus(StrEnum):
    JOINED = "joined"
    CANCELLED = "cancelled"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
