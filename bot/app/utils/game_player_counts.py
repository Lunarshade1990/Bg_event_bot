from __future__ import annotations

from typing import Iterable


def calculate_game_max_players_with_expansions(game: dict, expansions: list[dict] | None = None) -> int | None:
    max_players = game.get("max_players")
    if max_players is None:
        return None
    if game.get("game_type") != "base":
        return max_players

    total = max_players
    for expansion in expansions or []:
        exp_max_players = expansion.get("max_players")
        if exp_max_players is None:
            continue
        total += max(exp_max_players - max_players, 0)
    return total


def calculate_max_for_all_selected_games(
    selected_games: Iterable[dict],
    owned_expansions: list[dict] | None = None,
) -> int | None:
    owned_expansions_by_base_bgg_id: dict[int, list[dict]] = {}
    for expansion in owned_expansions or []:
        for base_bgg_id in expansion.get("bgg_expands_ids_cached") or []:
            owned_expansions_by_base_bgg_id.setdefault(base_bgg_id, []).append(expansion)

    effective_max_values: list[int] = []
    for game in selected_games:
        max_players = game.get("max_players")
        if max_players is None:
            continue

        if game.get("game_type") == "base" and game.get("bgg_id") is not None:
            expansions = owned_expansions_by_base_bgg_id.get(game["bgg_id"], [])
            effective_max = calculate_game_max_players_with_expansions(game, expansions)
        else:
            effective_max = max_players

        if effective_max is not None:
            effective_max_values.append(effective_max)

    if not effective_max_values:
        return None
    return min(effective_max_values)
