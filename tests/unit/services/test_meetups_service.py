from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.app.schemas.meetup import MeetupCreateRequest
from backend.app.services import meetups as meetup_service
from tests.fixtures.meetups import make_meetup, make_user


def test_join_meetup_rejects_when_full(db_session: Session) -> None:
    creator = make_user(db_session, telegram_id=30001, display_name="Creator")
    guest = make_user(db_session, telegram_id=30002, display_name="Guest")
    meetup = make_meetup(db_session, creator, capacity_total=2)

    meetup_service.join_meetup(db_session, meetup.id, guest.id)
    outsider = make_user(db_session, telegram_id=30003, display_name="Outsider")

    with pytest.raises(meetup_service.MeetupCapacityFullError):
        meetup_service.join_meetup(db_session, meetup.id, outsider.id)


def test_create_meetup_requires_existing_creator(db_session: Session) -> None:
    payload = MeetupCreateRequest(
        creator_user_id=999999,
        scheduled_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        capacity_total=3,
    )

    with pytest.raises(meetup_service.MeetupNotFoundError):
        meetup_service.create_meetup(db_session, payload)


def test_leave_meetup_is_idempotent(db_session: Session) -> None:
    creator = make_user(db_session, telegram_id=30100, display_name="Creator")
    guest = make_user(db_session, telegram_id=30101, display_name="Guest")
    meetup = make_meetup(db_session, creator, capacity_total=3)

    meetup_service.join_meetup(db_session, meetup.id, guest.id)
    left = meetup_service.leave_meetup(db_session, meetup.id, guest.id)
    assert len(left.participants) == 1

    left_again = meetup_service.leave_meetup(db_session, meetup.id, guest.id)
    assert len(left_again.participants) == 1
