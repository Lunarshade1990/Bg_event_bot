from fastapi.testclient import TestClient

from backend.app.db.models.enums import CampaignSource, GameType, OwnershipSource
from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def test_randomizer_is_shared_by_bgg_username_and_survives_collection_removal(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    owner = User(telegram_id=71001, display_name="Owner", bgg_username=" Shared_BGG ")
    spouse = User(telegram_id=71002, display_name="Spouse", bgg_username="shared_bgg")
    unrelated = User(telegram_id=71003, display_name="Other", bgg_username="other_bgg")
    game = Game(
        bgg_id=71001,
        title="Spirit Island",
        min_players=1,
        max_players=4,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    unowned_game = Game(
        bgg_id=71002,
        title="Azul",
        min_players=2,
        max_players=4,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([owner, spouse, unrelated, game, unowned_game])
    db_session.flush()
    db_session.add(
        UserGame(
            user_id=owner.id,
            game_id=game.id,
            source=OwnershipSource.BGG_IMPORT,
            is_available_for_meetups=True,
        )
    )
    db_session.commit()

    listed = client.get(
        "/api/randomizers/games",
        headers=api_headers,
        params={"telegram_id": spouse.telegram_id},
    )
    assert listed.status_code == 200
    listed_ids = [item["id"] for item in listed.json()]
    assert game.id in listed_ids
    assert unowned_game.id in listed_ids
    assert listed_ids.index(game.id) < listed_ids.index(unowned_game.id)

    created = client.post(
        f"/api/randomizers/{game.id}/categories",
        headers=api_headers,
        params={"telegram_id": owner.telegram_id},
        json={"name": "Духи", "draw_count": None},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    added = client.post(
        f"/api/randomizers/{game.id}/categories/{category_id}/options",
        headers=api_headers,
        params={"telegram_id": owner.telegram_id},
        json={"values": ["Дух грома", "Хранитель леса", "Океанские глубины"]},
    )
    assert added.status_code == 200

    shared_config = client.get(
        f"/api/randomizers/{game.id}",
        headers=api_headers,
        params={"telegram_id": spouse.telegram_id},
    )
    assert shared_config.status_code == 200
    assert shared_config.json()["categories"][0]["name"] == "Духи"
    assert len(shared_config.json()["categories"][0]["options"]) == 3

    draw = client.post(
        f"/api/randomizers/{game.id}/draw",
        headers=api_headers,
        params={"telegram_id": spouse.telegram_id},
        json={"category_ids": [category_id], "player_count": 2},
    )
    assert draw.status_code == 200
    drawn_options = draw.json()["categories"][0]["selected"]
    assert len(drawn_options) == 2
    assert len(set(drawn_options)) == 2

    db_session.query(UserGame).filter_by(user_id=owner.id, game_id=game.id).delete()
    db_session.commit()
    still_available = client.get(
        f"/api/randomizers/{game.id}",
        headers=api_headers,
        params={"telegram_id": spouse.telegram_id},
    )
    assert still_available.status_code == 200
    assert len(still_available.json()["categories"][0]["options"]) == 3

    private_config = client.get(
        f"/api/randomizers/{game.id}",
        headers=api_headers,
        params={"telegram_id": unrelated.telegram_id},
    )
    assert private_config.status_code == 200
    assert private_config.json()["categories"] == []
    private_update = client.patch(
        f"/api/randomizers/{game.id}/categories/{category_id}",
        headers=api_headers,
        params={"telegram_id": unrelated.telegram_id},
        json={"name": "Hijacked"},
    )
    assert private_update.status_code == 404


def test_randomizer_shortage_returns_no_partial_category_result(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    owner = User(telegram_id=72001, display_name="Owner", bgg_username="shortage_bgg")
    game = Game(
        bgg_id=72001,
        title="Test Game",
        min_players=1,
        max_players=4,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([owner, game])
    db_session.commit()

    category = client.post(
        f"/api/randomizers/{game.id}/categories",
        headers=api_headers,
        params={"telegram_id": owner.telegram_id},
        json={"name": "Нации", "draw_count": 3},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]
    options = client.post(
        f"/api/randomizers/{game.id}/categories/{category_id}/options",
        headers=api_headers,
        params={"telegram_id": owner.telegram_id},
        json={"values": ["Первая"]},
    )
    assert options.status_code == 200

    draw = client.post(
        f"/api/randomizers/{game.id}/draw",
        headers=api_headers,
        params={"telegram_id": owner.telegram_id},
        json={"category_ids": [category_id]},
    )
    assert draw.status_code == 200
    result = draw.json()["categories"][0]
    assert result["requested_count"] == 3
    assert result["available_count"] == 1
    assert result["shortage"] == 2
    assert result["selected"] == []
