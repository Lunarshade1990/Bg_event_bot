

from collections import defaultdict

from bot.app.services.backend_api import BackendAPIClient
from bot.app.utils.game_player_counts import calculate_game_max_players_with_expansions

backend_client = BackendAPIClient()
BACKEND_GAMES_BATCH_SIZE = 100


async def load_owned_games(
    owner_id: int,
) -> list[dict]:
    games: list[dict] = []
    offset = 0

    while True:
        batch = await backend_client.list_games(
            owner_id=owner_id,
            limit=BACKEND_GAMES_BATCH_SIZE,
            offset=offset,
        )
        games.extend(batch)
        if len(batch) < BACKEND_GAMES_BATCH_SIZE:
            return _group_owned_games(games)
        offset += BACKEND_GAMES_BATCH_SIZE


def _group_owned_games(games: list[dict]) -> list[dict]:
    base_games_by_bgg_id = {
        game["bgg_id"]: game
        for game in games
        if game.get("game_type") == "base"
    }
    owned_expansions_by_base_id: dict[int, list[dict]] = defaultdict(list)
    attached_expansion_ids: set[int] = set()

    for game in games:
        if game.get("game_type") != "expansion":
            continue

        matched_base_games = _match_owned_base_games(
            game,
            base_games_by_bgg_id=base_games_by_bgg_id,
        )
        if len(matched_base_games) != 1:
            continue

        base_game = matched_base_games[0]
        owned_expansions_by_base_id[base_game["id"]].append(game)
        attached_expansion_ids.add(game["id"])

    entries: list[dict] = []
    for game in games:
        if game.get("game_type") == "base":
            expansions = sorted(
                owned_expansions_by_base_id.get(game["id"], []),
                key=lambda item: item["title"].lower(),
            )
            entries.append(_build_grouped_entry(game, expansions))
            continue

        if game["id"] not in attached_expansion_ids:
            entries.append(_build_grouped_entry(game, []))

    return entries


def _match_owned_base_games(
    game: dict,
    *,
    base_games_by_bgg_id: dict[int, dict],
) -> list[dict]:
    matched_base_games: list[dict] = []
    for base_bgg_id in game.get("bgg_expands_ids_cached") or []:
        base_game = base_games_by_bgg_id.get(base_bgg_id)
        if base_game is not None:
            matched_base_games.append(base_game)
    return matched_base_games



def _build_grouped_entry(game: dict, expansions: list[dict]) -> dict:
    display_max_players = calculate_game_max_players_with_expansions(game, expansions)
    if display_max_players is None:
        display_max_players = game["max_players"]

    return {
        "game": game,
        "expansions": expansions,
        "display_min_players": game["min_players"],
        "display_max_players": display_max_players,
    }
    
