from datetime import UTC, datetime

from fastapi.testclient import TestClient

from tests.fixtures.meetups import make_meetup, make_user


def test_create_meetup_adds_creator_as_participant(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20001, display_name="Creator")

    response = client.post(
        "/api/meetups",
        headers=api_headers,
        json={
            "creator_user_id": creator.id,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 5,
            "comment": "Bring snacks",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["capacity_total"] == 5
    assert payload["comment"] == "Bring snacks"
    assert payload["status"] == "planned"
    assert payload["creator_user_id"] == creator.id
    assert payload["telegram_chat_id"] is None
    assert payload["telegram_thread_id"] is None
    assert payload["telegram_message_id"] is None
    assert len(payload["participants"]) == 1
    assert payload["participants"][0]["telegram_id"] == 20001
    assert payload["participants"][0]["status"] == "joined"


def test_create_meetup_with_telegram_thread_data(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20009, display_name="Creator")

    response = client.post(
        "/api/meetups",
        headers=api_headers,
        json={
            "creator_user_id": creator.id,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": "Group meetup",
            "telegram_chat_id": 123456,
            "telegram_thread_id": 987654,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["telegram_chat_id"] == 123456
    assert payload["telegram_thread_id"] == 987654
    assert payload["telegram_message_id"] is None


def test_create_and_get_telegram_chat_topic(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/meetups/telegram-topics",
        headers=api_headers,
        json={
            "telegram_chat_id": 314159,
            "telegram_thread_id": 271828,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["telegram_chat_id"] == 314159
    assert payload["telegram_thread_id"] == 271828

    get_response = client.get(
        "/api/meetups/telegram-topics/314159",
        headers=api_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_create_and_get_telegram_chat_topic_accepts_negative_group_id(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/meetups/telegram-topics",
        headers=api_headers,
        json={
            "telegram_chat_id": -100314159,
            "telegram_thread_id": 271828,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["telegram_chat_id"] == -100314159
    assert payload["telegram_thread_id"] == 271828

    get_response = client.get(
        "/api/meetups/telegram-topics/-100314159",
        headers=api_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_list_and_get_meetup(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20002, display_name="Lister")
    meetup = make_meetup(
        db_session,
        creator,
        scheduled_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        capacity_total=3,
        comment="Friday games",
    )

    list_response = client.get("/api/meetups", headers=api_headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["id"] == meetup.id for item in listed)
    selected = next(item for item in listed if item["id"] == meetup.id)
    assert selected["participants"][0]["telegram_id"] == 20002

    get_response = client.get(f"/api/meetups/{meetup.id}", headers=api_headers)
    assert get_response.status_code == 200
    assert get_response.json()["comment"] == "Friday games"


def test_list_meetups_filter_by_telegram_chat_id(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20010, display_name="Creator")
    make_meetup(
        db_session,
        creator,
        scheduled_at=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        capacity_total=4,
        comment="Group meetup",
        telegram_chat_id=123456,
        telegram_thread_id=987654,
    )
    make_meetup(
        db_session,
        creator,
        scheduled_at=datetime(2026, 8, 2, 18, 0, tzinfo=UTC),
        capacity_total=4,
        comment="Another meetup",
    )

    response = client.get(
        "/api/meetups?telegram_chat_id=123456",
        headers=api_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert all(item["telegram_chat_id"] == 123456 for item in payload)
    assert any(item["telegram_thread_id"] == 987654 for item in payload)


def test_join_meetup_and_capacity_full(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20003, display_name="Host")
    guest = make_user(db_session, telegram_id=20004, display_name="Guest", username="guest_user")
    meetup = make_meetup(
        db_session,
        creator,
        scheduled_at=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        capacity_total=2,
    )

    join_response = client.post(
        f"/api/meetups/{meetup.id}/join",
        headers=api_headers,
        json={"user_id": guest.id},
    )
    assert join_response.status_code == 200
    participants = join_response.json()["participants"]
    assert len(participants) == 2
    telegram_ids = {item["telegram_id"] for item in participants}
    assert telegram_ids == {20003, 20004}

    outsider = make_user(db_session, telegram_id=20005, display_name="Outsider")
    full_response = client.post(
        f"/api/meetups/{meetup.id}/join",
        headers=api_headers,
        json={"user_id": outsider.id},
    )
    assert full_response.status_code == 409


def test_leave_meetup_removes_user_from_joined_list(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20100, display_name="Host")
    guest = make_user(db_session, telegram_id=20101, display_name="Guest", username="guest_user")
    meetup = make_meetup(db_session, creator, capacity_total=3)

    join_response = client.post(
        f"/api/meetups/{meetup.id}/join",
        headers=api_headers,
        json={"user_id": guest.id},
    )
    assert join_response.status_code == 200
    assert len(join_response.json()["participants"]) == 2

    leave_response = client.post(
        f"/api/meetups/{meetup.id}/leave",
        headers=api_headers,
        json={"user_id": guest.id},
    )
    assert leave_response.status_code == 200
    participants = leave_response.json()["participants"]
    assert len(participants) == 1
    assert participants[0]["telegram_id"] == 20100


def test_set_meetup_telegram_message_id(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20200, display_name="Creator")
    meetup = make_meetup(db_session, creator, capacity_total=2)

    response = client.post(
        f"/api/meetups/{meetup.id}/telegram-message",
        headers=api_headers,
        json={"telegram_message_id": 12345},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["telegram_message_id"] == 12345


def test_join_meetup_already_joined_returns_conflict(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20006, display_name="Host Again")
    meetup = make_meetup(db_session, creator, capacity_total=4)

    duplicate_response = client.post(
        f"/api/meetups/{meetup.id}/join",
        headers=api_headers,
        json={"user_id": creator.id},
    )
    assert duplicate_response.status_code == 409


def test_delete_meetup_permissions_and_not_found(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20007, display_name="Owner")
    stranger = make_user(db_session, telegram_id=20008, display_name="Stranger")
    meetup = make_meetup(db_session, creator, capacity_total=4)

    forbidden_response = client.request(
        "DELETE",
        f"/api/meetups/{meetup.id}",
        headers=api_headers,
        json={"requesting_user_id": stranger.id},
    )
    assert forbidden_response.status_code == 403

    delete_response = client.request(
        "DELETE",
        f"/api/meetups/{meetup.id}",
        headers=api_headers,
        json={"requesting_user_id": creator.id},
    )
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/meetups/{meetup.id}", headers=api_headers)
    assert missing_response.status_code == 404


def test_create_meetup_unknown_creator_returns_not_found(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/meetups",
        headers=api_headers,
        json={
            "creator_user_id": 999999,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 2,
        },
    )
    assert response.status_code == 404
