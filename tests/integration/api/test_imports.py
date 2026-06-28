from fastapi.testclient import TestClient

from backend.app.db.models.bgg_import_job import BggImportJob
from backend.app.db.models.enums import CampaignSource, GameType, OwnershipSource
from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


class FakeCollectionItem:
    def __init__(
        self,
        game_id: int,
        name: str,
        *,
        own: str | None = "1",
        preordered: str = "0",
        prevowned: str = "0",
        want: str = "0",
        wanttobuy: str = "0",
        wanttoplay: str = "0",
        fortrade: str = "0",
        wishlist: str = "0",
    ) -> None:
        self.id = game_id
        self.name = name
        self._data = {}
        if own is not None:
            self._data["own"] = own
        self._data["preordered"] = preordered
        self._data["prevowned"] = prevowned
        self._data["want"] = want
        self._data["wanttobuy"] = wanttobuy
        self._data["wanttoplay"] = wanttoplay
        self._data["fortrade"] = fortrade
        self._data["wishlist"] = wishlist

    @property
    def owned(self) -> bool:
        return bool(int(self._data.get("own", 0)))

    @property
    def preordered(self) -> bool:
        return bool(int(self._data.get("preordered", 0)))

    @property
    def prev_owned(self) -> bool:
        return bool(int(self._data.get("prevowned", 0)))

    @property
    def want(self) -> bool:
        return bool(int(self._data.get("want", 0)))

    @property
    def want_to_buy(self) -> bool:
        return bool(int(self._data.get("wanttobuy", 0)))

    @property
    def want_to_play(self) -> bool:
        return bool(int(self._data.get("wanttoplay", 0)))

    @property
    def for_trade(self) -> bool:
        return bool(int(self._data.get("fortrade", 0)))

    @property
    def wishlist(self) -> bool:
        return bool(int(self._data.get("wishlist", 0)))


class FakeRelatedGame:
    def __init__(self, game_id: int) -> None:
        self.id = game_id


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
        expands: list[FakeRelatedGame] | None = None,
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
        self.expands = expands or []


class FakeBGGClient:
    def collection(self, user_name: str, subtype: str, own: bool = True):
        if subtype == "boardgame":
            return [
                FakeCollectionItem(1001, "Gloomhaven"),
                FakeCollectionItem(1003, "No Status", own="0"),
            ]
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
                expands=[],
            )
        if game_id == 1003:
            return FakeGameDetails(
                name="No Status",
                min_players=2,
                max_players=5,
                playing_time=90,
                image="https://example.com/no-status.jpg",
                designers=["Unknown Designer"],
                mechanics=[],
                expands=[],
            )
        return FakeGameDetails(
            name="Forgotten Circles",
            min_players=1,
            max_players=4,
            playing_time=180,
            image="https://example.com/forgotten-circles.jpg",
            designers=["Isaac Childres", "Marcel Cwertetsck"],
            mechanics=["Campaign Game"],
            expands=[FakeRelatedGame(1001)],
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
    assert body["processed_games"] == 3
    assert body["created_games"] == 3
    assert body["linked_games"] == 3
    assert body["collection_games_count"] == 3

    imported_games = db_session.query(Game).filter(Game.bgg_id.in_([1001, 1002, 1003])).count()
    imported_links = db_session.query(UserGame).filter(UserGame.user_id == user.id).count()
    import_jobs = db_session.query(BggImportJob).filter(BggImportJob.user_id == user.id).count()
    expansion = db_session.query(Game).filter(Game.bgg_id == 1002).one()

    assert imported_games == 3
    assert imported_links == 3
    assert import_jobs == 1
    assert expansion.bgg_expands_ids_cached == [1001]


def test_import_bgg_collection_stores_zero_play_time_as_null(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
    monkeypatch,
) -> None:
    user = User(
        telegram_id=111222,
        display_name="ZeroTimeUser",
        bgg_username="zero_time_bgg",
    )
    db_session.add(user)
    db_session.commit()

    class FakeZeroTimeClient:
        def collection(self, user_name: str, subtype: str, own: bool = True):
            return [FakeCollectionItem(3001, "Zero Time Game")]

        def game(self, game_id: int):
            return FakeGameDetails(
                name="Zero Time Game",
                min_players=1,
                max_players=4,
                playing_time=0,
                image="https://example.com/zero-time.jpg",
                designers=["Designer"],
                mechanics=[],
                expands=[],
            )

    monkeypatch.setattr("backend.app.services.bgg_import.get_bgg_client", lambda: FakeZeroTimeClient())

    response = client.post(
        "/api/imports/bgg/collection",
        headers=api_headers,
        json={"telegram_id": 111222, "bgg_username": "zero_time_bgg"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed_games"] == 1
    assert body["created_games"] == 1
    assert body["linked_games"] == 1

    imported_game = db_session.query(Game).filter(Game.bgg_id == 3001).one()
    assert imported_game.play_time_minutes is None


def test_import_bgg_collection_removes_missing_bgg_owned_games(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
    monkeypatch,
) -> None:
    user = User(
        telegram_id=123456,
        display_name="Collector",
        bgg_username="collector_bgg",
    )
    first_game = Game(
        bgg_id=2001,
        title="Existing One",
        original_title="Existing One",
        author="Designer",
        min_players=1,
        max_players=4,
        play_time_minutes=60,
        image_url="https://example.com/one.jpg",
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    second_game = Game(
        bgg_id=2002,
        title="Existing Two",
        original_title="Existing Two",
        author="Designer",
        min_players=1,
        max_players=4,
        play_time_minutes=60,
        image_url="https://example.com/two.jpg",
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([user, first_game, second_game])
    db_session.flush()
    db_session.add_all(
        [
            UserGame(user_id=user.id, game_id=first_game.id, source=OwnershipSource.BGG_IMPORT),
            UserGame(user_id=user.id, game_id=second_game.id, source=OwnershipSource.BGG_IMPORT),
        ]
    )
    db_session.commit()

    class FakeSyncClient:
        def collection(self, user_name: str, subtype: str, own: bool = True):
            if subtype == "boardgame":
                return [FakeCollectionItem(2001, "Existing One", own="1")]
            return [FakeCollectionItem(2002, "Existing Two", own="0", prevowned="1")]

        def game(self, game_id: int):
            return FakeGameDetails(
                name="Existing One" if game_id == 2001 else "Existing Two",
                min_players=1,
                max_players=4,
                playing_time=60,
                image="https://example.com/game.jpg",
                designers=["Designer"],
                mechanics=[],
                expands=[FakeRelatedGame(2001)] if game_id == 2002 else [],
            )

    monkeypatch.setattr("backend.app.services.bgg_import.get_bgg_client", lambda: FakeSyncClient())

    response = client.post(
        "/api/imports/bgg/collection",
        headers=api_headers,
        json={"telegram_id": 123456, "bgg_username": "collector_bgg"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed_games"] == 1
    assert body["collection_games_count"] == 1
    user_games = db_session.query(UserGame).filter(UserGame.user_id == user.id).all()

    assert len(user_games) == 1
    assert user_games[0].game_id == first_game.id
