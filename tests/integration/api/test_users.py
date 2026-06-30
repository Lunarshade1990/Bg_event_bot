from fastapi.testclient import TestClient

from backend.app.db.models.enums import CampaignSource, GameType, OwnershipSource
from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def test_sync_telegram_user_creates_user(client: TestClient, api_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/users/telegram",
        headers=api_headers,
        json={
            "telegram_id": 123456,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "Smith",
            "bgg_username": "alice_bgg",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["telegram_id"] == 123456
    assert body["display_name"] == "Alice Smith"
    assert body["bgg_username"] == "alice_bgg"


def test_get_user_by_telegram_id_returns_synced_user(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/users/telegram",
        headers=api_headers,
        json={
            "telegram_id": 555001,
            "username": "boardgamer",
            "display_name": "Board Gamer",
        },
    )
    created_user = create_response.json()

    response = client.get(
        f"/api/users/by-telegram/{created_user['telegram_id']}",
        headers=api_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]


def test_list_users_with_games_excludes_requested_user(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    current_user = User(telegram_id=40001, display_name="Current User", username="current_user")
    other_user = User(
        telegram_id=40002,
        display_name="Other User",
        username="other_user",
        bgg_username="other_bgg",
    )
    empty_user = User(telegram_id=40003, display_name="Empty User")
    game = Game(
        bgg_id=401,
        title="Catan",
        author="Klaus Teuber",
        min_players=2,
        max_players=4,
        play_time_minutes=90,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([current_user, other_user, empty_user, game])
    db_session.flush()
    db_session.add(
        UserGame(
            user_id=other_user.id,
            game_id=game.id,
            source=OwnershipSource.BGG_IMPORT,
            is_available_for_meetups=True,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/users",
        headers=api_headers,
        params={"has_games": True, "exclude_user_id": current_user.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == other_user.id
    assert body[0]["username"] == "other_user"
    assert body[0]["bgg_username"] == "other_bgg"
