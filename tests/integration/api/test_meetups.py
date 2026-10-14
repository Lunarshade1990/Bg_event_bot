from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.db.models.enums import (
    CampaignSource,
    GameType,
    MeetupStatus,
    OwnershipSource,
)
from backend.app.db.models.game import Game
from backend.app.db.models.user_game import UserGame
from backend.app.services import meetups as meetup_service
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


def test_create_meetup_persists_game_ids_in_response(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20009, display_name="Creator")
    game = Game(
        bgg_id=1001,
        title="Catan",
        author="Klaus Teuber",
        min_players=3,
        max_players=4,
        play_time_minutes=90,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add(game)
    db_session.commit()

    response = client.post(
        "/api/meetups",
        headers=api_headers,
        json={
            "creator_user_id": creator.id,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "game_ids": [game.id],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload["games"]) == 1
    assert payload["games"][0]["id"] == game.id
    assert payload["games"][0]["title"] == "Catan"


def test_meetup_proposal_sources_put_creator_first_and_include_joined_collectors(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20090, display_name="Creator")
    creator.bgg_username = "creator_bgg"
    participant = make_user(db_session, telegram_id=20091, display_name="Participant")
    participant.bgg_username = "participant_bgg"
    outsider = make_user(db_session, telegram_id=20092, display_name="Outsider")
    outsider.bgg_username = "outsider_bgg"

    games = [
        Game(
            bgg_id=20090 + index,
            title=f"Game {index}",
            min_players=1,
            max_players=4,
            game_type=GameType.BASE,
            campaign_source=CampaignSource.UNKNOWN,
        )
        for index in range(3)
    ]
    db_session.add_all(games)
    db_session.flush()
    for user, game in zip((creator, participant, outsider), games, strict=True):
        db_session.add(
            UserGame(
                user_id=user.id,
                game_id=game.id,
                source=OwnershipSource.BGG_IMPORT,
            )
        )
    db_session.commit()

    meetup = make_meetup(db_session, creator)
    meetup_service.join_meetup(db_session, meetup.id, participant.id)

    response = client.get(f"/api/meetups/{meetup.id}", headers=api_headers)

    assert response.status_code == 200
    sources = response.json()["proposal_sources"]
    assert [source["user_id"] for source in sources] == [creator.id, participant.id]


def test_meetup_suggestion_replaces_previous_games_for_proposer(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20100, display_name="Creator")
    creator.bgg_username = "creator_bgg"
    proposer = make_user(db_session, telegram_id=20101, display_name="Proposer", username="player")
    proposer.bgg_username = "proposer_bgg"
    games = [
        Game(
            bgg_id=20100 + index,
            title=f"Game {index}",
            min_players=1,
            max_players=4,
            game_type=GameType.BASE,
            campaign_source=CampaignSource.UNKNOWN,
        )
        for index in range(3)
    ]
    db_session.add_all(games)
    db_session.flush()
    db_session.add_all(
        [
            UserGame(
                user_id=creator.id,
                game_id=games[0].id,
                source=OwnershipSource.BGG_IMPORT,
            ),
            UserGame(
                user_id=creator.id,
                game_id=games[1].id,
                source=OwnershipSource.BGG_IMPORT,
            ),
            UserGame(
                user_id=proposer.id,
                game_id=games[2].id,
                source=OwnershipSource.BGG_IMPORT,
            ),
        ]
    )
    db_session.commit()
    meetup = make_meetup(db_session, creator)

    first_response = client.post(
        f"/api/meetups/{meetup.id}/suggestions",
        headers=api_headers,
        json={
            "proposer_user_id": proposer.id,
            "collection_owner_user_id": creator.id,
            "game_ids": [games[0].id, games[1].id],
        },
    )
    assert first_response.status_code == 200
    assert len(first_response.json()["game_suggestions"][0]["games"]) == 2

    replacement_response = client.post(
        f"/api/meetups/{meetup.id}/suggestions",
        headers=api_headers,
        json={
            "proposer_user_id": proposer.id,
            "collection_owner_user_id": proposer.id,
            "game_ids": [games[2].id],
        },
    )

    assert replacement_response.status_code == 200
    suggestions = replacement_response.json()["game_suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["proposer_user_id"] == proposer.id
    assert suggestions[0]["username"] == "player"
    assert [game["id"] for game in suggestions[0]["games"]] == [games[2].id]


def test_nonparticipant_can_toggle_votes_for_suggested_games(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20120, display_name="Creator")
    voter = make_user(
        db_session, telegram_id=20121, display_name="Outside player", username="outside"
    )
    games = [
        Game(
            bgg_id=20120 + index,
            title=f"Vote game {index}",
            min_players=1,
            max_players=4,
            game_type=GameType.BASE,
            campaign_source=CampaignSource.UNKNOWN,
        )
        for index in range(2)
    ]
    db_session.add_all(games)
    db_session.flush()
    db_session.add_all(
        UserGame(
            user_id=creator.id,
            game_id=game.id,
            source=OwnershipSource.BGG_IMPORT,
        )
        for game in games
    )
    db_session.commit()
    meetup = make_meetup(db_session, creator)

    suggestion_response = client.post(
        f"/api/meetups/{meetup.id}/suggestions",
        headers=api_headers,
        json={
            "proposer_user_id": creator.id,
            "collection_owner_user_id": creator.id,
            "game_ids": [games[0].id],
        },
    )
    assert suggestion_response.status_code == 200

    vote_url = f"/api/meetups/{meetup.id}/game-votes"
    vote_payload = {"user_id": voter.id, "game_id": games[0].id}
    added_vote = client.post(vote_url, headers=api_headers, json=vote_payload)
    assert added_vote.status_code == 200
    vote_summary = added_vote.json()["game_suggestion_votes"]
    assert vote_summary == [
        {
            "game_id": games[0].id,
            "voters": [
                {
                    "user_id": voter.id,
                    "display_name": "Outside player",
                    "username": "outside",
                }
            ],
        }
    ]
    assert len(added_vote.json()["participants"]) == 1

    removed_vote = client.post(vote_url, headers=api_headers, json=vote_payload)
    assert removed_vote.status_code == 200
    assert removed_vote.json()["game_suggestion_votes"][0]["voters"] == []

    client.post(vote_url, headers=api_headers, json=vote_payload)
    replaced_suggestion = client.post(
        f"/api/meetups/{meetup.id}/suggestions",
        headers=api_headers,
        json={
            "proposer_user_id": creator.id,
            "collection_owner_user_id": creator.id,
            "game_ids": [games[1].id],
        },
    )
    assert replaced_suggestion.status_code == 200
    assert replaced_suggestion.json()["game_suggestion_votes"] == [
        {"game_id": games[1].id, "voters": []}
    ]

    invalid_vote = client.post(
        vote_url,
        headers=api_headers,
        json={"user_id": voter.id, "game_id": games[0].id},
    )
    assert invalid_vote.status_code == 400
    assert invalid_vote.json()["detail"] == "The game has not been suggested for this meetup."

    meetup.status = MeetupStatus.COMPLETED
    db_session.commit()
    closed_vote = client.post(
        vote_url,
        headers=api_headers,
        json={"user_id": voter.id, "game_id": games[1].id},
    )
    assert closed_vote.status_code == 400
    assert closed_vote.json()["detail"] == "Meetup is not open for voting."


def test_meetup_suggestion_rejects_games_outside_selected_collection(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20110, display_name="Creator")
    creator.bgg_username = "creator_bgg"
    proposer = make_user(db_session, telegram_id=20111, display_name="Proposer")
    game = Game(
        bgg_id=20110,
        title="Not owned by creator",
        min_players=1,
        max_players=4,
        game_type=GameType.BASE,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add(game)
    db_session.flush()
    db_session.add(
        UserGame(
            user_id=proposer.id,
            game_id=game.id,
            source=OwnershipSource.BGG_IMPORT,
        )
    )
    db_session.commit()
    meetup = make_meetup(db_session, creator)

    response = client.post(
        f"/api/meetups/{meetup.id}/suggestions",
        headers=api_headers,
        json={
            "proposer_user_id": proposer.id,
            "collection_owner_user_id": creator.id,
            "game_ids": [game.id],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "One or more selected games are not in the selected collection."
    )


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
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
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


def test_list_meetups_separates_upcoming_and_archive(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20011, display_name="Archive tester")
    now = datetime.now(UTC)
    upcoming = make_meetup(
        db_session,
        creator,
        scheduled_at=now + timedelta(days=2),
        capacity_total=4,
    )
    past = make_meetup(
        db_session,
        creator,
        scheduled_at=now - timedelta(days=2),
        capacity_total=4,
    )
    past.status = MeetupStatus.COMPLETED
    db_session.commit()

    upcoming_response = client.get(
        "/api/meetups",
        headers=api_headers,
        params={"archive": False},
    )
    archive_response = client.get(
        "/api/meetups",
        headers=api_headers,
        params={"archive": True},
    )

    assert upcoming_response.status_code == 200
    assert archive_response.status_code == 200
    assert {item["id"] for item in upcoming_response.json()} == {upcoming.id}
    assert {item["id"] for item in archive_response.json()} == {past.id}


def test_list_meetups_filter_by_telegram_chat_id(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    creator = make_user(db_session, telegram_id=20010, display_name="Creator")
    make_meetup(
        db_session,
        creator,
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
        capacity_total=4,
        comment="Group meetup",
        telegram_chat_id=123456,
        telegram_thread_id=987654,
    )
    make_meetup(
        db_session,
        creator,
        scheduled_at=datetime.now(UTC) + timedelta(days=2),
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
