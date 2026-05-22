from fastapi.testclient import TestClient

from backend.app.db.models.bgg_import_job import BggImportJob
from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


class FakeCollectionItem:
    def __init__(self, game_id: int, name: str) -> None:
        self.id = game_id
        self.name = name


class FakeGameDetails:
    def __init__(
        self,
        *,
        name: str,
        min_players: int,
        max_players: int,
        playing_time: int,
        image: str,
        designers: list[str],
        mechanics: list[str],
    ) -> None:
        self.name = name
        self.min_players = min_players
        self.max_players = max_players
        self.playing_time = playing_time
        self.max_playing_time = playing_time
        self.min_playing_time = playing_time
        self.image = image
        self.thumbnail = image
        self.designers = designers
        self.mechanics = mechanics


class FakeBGGClient:
    def collection(self, user_name: str, subtype: str, own: bool = True):
        if subtype == "boardgame":
            return [FakeCollectionItem(1001, "Gloomhaven")]
        return [FakeCollectionItem(1002, "Forgotten Circles")]

    def game(self, game_id: int):
        if game_id == 1001:
            return FakeGameDetails(
                name="Gloomhaven",
                min_players=1,
                max_players=4,
                playing_time=180,
                image="https://example.com/gloomhaven.jpg",
                designers=["Isaac Childres"],
                mechanics=["Campaign Game", "Hand Management"],
            )
        return FakeGameDetails(
            name="Forgotten Circles",
            min_players=1,
            max_players=4,
            playing_time=180,
            image="https://example.com/forgotten-circles.jpg",
            designers=["Isaac Childres", "Marcel Cwertetsck"],
            mechanics=["Campaign Game"],
        )


def test_import_bgg_collection_creates_games_and_ownership(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
    monkeypatch,
) -> None:
    user = User(
        telegram_id=987654,
        display_name="Importer",
        bgg_username="importer_bgg",
    )
    db_session.add(user)
    db_session.commit()

    monkeypatch.setattr("backend.app.services.bgg_import.get_bgg_client", lambda: FakeBGGClient())

    response = client.post(
        "/api/imports/bgg/collection",
        headers=api_headers,
        json={"telegram_id": 987654, "bgg_username": "importer_bgg"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed_games"] == 2
    assert body["created_games"] == 2
    assert body["linked_games"] == 2

    assert db_session.query(Game).count() == 2
    assert db_session.query(UserGame).count() == 2
    assert db_session.query(BggImportJob).count() == 1
