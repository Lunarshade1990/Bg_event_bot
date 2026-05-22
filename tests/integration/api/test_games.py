from fastapi.testclient import TestClient

from backend.app.db.models.enums import CampaignSource, GameType, OwnershipSource
from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def test_list_games_returns_filtered_results(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    owner = User(telegram_id=10001, display_name="Owner One")
    game_one = Game(
        bgg_id=111,
        title="Terraforming Mars",
        author="Jacob Fryxelius",
        min_players=1,
        max_players=5,
        play_time_minutes=120,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    game_two = Game(
        bgg_id=222,
        title="Gloomhaven",
        author="Isaac Childres",
        min_players=1,
        max_players=4,
        play_time_minutes=180,
        game_type=GameType.BASE,
        has_campaign=True,
        campaign_source=CampaignSource.BGG,
    )
    db_session.add_all([owner, game_one, game_two])
    db_session.flush()
    db_session.add(
        UserGame(
            user_id=owner.id,
            game_id=game_two.id,
            source=OwnershipSource.BGG_IMPORT,
            is_available_for_meetups=True,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/games",
        headers=api_headers,
        params={"title": "gloom", "has_campaign": "true", "players_count": 4},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Gloomhaven"


def test_list_games_filters_by_owner_with_pagination(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    owner = User(telegram_id=10011, display_name="Collector")
    other_user = User(telegram_id=10012, display_name="Guest")
    game_one = Game(
        bgg_id=411,
        title="Azul",
        author="Michael Kiesling",
        min_players=2,
        max_players=4,
        play_time_minutes=45,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    game_two = Game(
        bgg_id=412,
        title="Brass: Birmingham",
        author="Martin Wallace",
        min_players=2,
        max_players=4,
        play_time_minutes=120,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    game_three = Game(
        bgg_id=413,
        title="Clank!",
        author="Paul Dennen",
        min_players=2,
        max_players=4,
        play_time_minutes=60,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([owner, other_user, game_one, game_two, game_three])
    db_session.flush()
    db_session.add_all(
        [
            UserGame(
                user_id=owner.id,
                game_id=game_one.id,
                source=OwnershipSource.BGG_IMPORT,
                is_available_for_meetups=True,
            ),
            UserGame(
                user_id=owner.id,
                game_id=game_two.id,
                source=OwnershipSource.BGG_IMPORT,
                is_available_for_meetups=False,
            ),
            UserGame(
                user_id=other_user.id,
                game_id=game_three.id,
                source=OwnershipSource.BGG_IMPORT,
                is_available_for_meetups=True,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/games",
        headers=api_headers,
        params={"owner_id": owner.id, "limit": 1, "offset": 1},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": game_two.id,
            "bgg_id": 412,
            "title": "Brass: Birmingham",
            "original_title": None,
            "author": "Martin Wallace",
            "min_players": 2,
            "max_players": 4,
            "play_time_minutes": 120,
            "image_url": None,
            "game_type": "base",
            "has_campaign": False,
            "campaign_source": "unknown",
        }
    ]


def test_get_game_owners_returns_owner_list(
    client: TestClient,
    db_session,
    api_headers: dict[str, str],
) -> None:
    owner = User(
        telegram_id=10002,
        username="owner2",
        display_name="Owner Two",
        bgg_username="owner_two_bgg",
    )
    game = Game(
        bgg_id=333,
        title="Spirit Island",
        author="R. Eric Reuss",
        min_players=1,
        max_players=4,
        play_time_minutes=120,
        game_type=GameType.BASE,
        has_campaign=False,
        campaign_source=CampaignSource.UNKNOWN,
    )
    db_session.add_all([owner, game])
    db_session.flush()
    db_session.add(
        UserGame(
            user_id=owner.id,
            game_id=game.id,
            source=OwnershipSource.MANUAL,
            is_available_for_meetups=True,
            comment="Bring sleeves too",
        )
    )
    db_session.commit()

    response = client.get(f"/api/games/{game.id}/owners", headers=api_headers)

    assert response.status_code == 200
    assert response.json() == [
        {
            "user_id": owner.id,
            "display_name": "Owner Two",
            "username": "owner2",
            "bgg_username": "owner_two_bgg",
            "is_available_for_meetups": True,
            "comment": "Bring sleeves too",
        }
    ]
