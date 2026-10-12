from types import SimpleNamespace

import pytest

from backend.app.services import game_randomizers


def _category(
    category_id: int,
    name: str,
    draw_count: int | None,
    values: list[str],
) -> SimpleNamespace:
    return SimpleNamespace(
        id=category_id,
        name=name,
        draw_count=draw_count,
        options=[SimpleNamespace(value=value) for value in values],
    )


def _stub_randomizer_lookup(
    monkeypatch: pytest.MonkeyPatch,
    categories: list[SimpleNamespace],
) -> None:
    monkeypatch.setattr(
        game_randomizers.user_repository,
        "get_user_by_telegram_id",
        lambda db, telegram_id: SimpleNamespace(bgg_username="shared_bgg"),
    )
    monkeypatch.setattr(
        game_randomizers.randomizer_repository,
        "get_game",
        lambda db, game_id: SimpleNamespace(id=game_id),
    )
    monkeypatch.setattr(
        game_randomizers.randomizer_repository,
        "get_categories",
        lambda db, bgg_username, game_id: categories,
    )


def test_draw_uses_player_count_and_samples_without_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categories = [
        _category(1, "Духи", None, ["Дух 1", "Дух 2", "Дух 3"]),
        _category(2, "Сценарии", 1, ["Сценарий 1", "Сценарий 2"]),
    ]
    _stub_randomizer_lookup(monkeypatch, categories)

    _, results = game_randomizers.draw(
        None,
        telegram_id=1,
        game_id=5,
        category_ids=[1, 2],
        player_count=2,
    )

    assert len(results[0].selected) == 2
    assert len(set(results[0].selected)) == 2
    assert results[0].shortage == 0
    assert len(results[1].selected) == 1


def test_draw_reports_shortage_without_partial_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categories = [_category(1, "Нации", 3, ["Одна"])]
    _stub_randomizer_lookup(monkeypatch, categories)

    _, results = game_randomizers.draw(
        None,
        telegram_id=1,
        game_id=5,
        category_ids=[1],
        player_count=None,
    )

    assert results[0].requested_count == 3
    assert results[0].available_count == 1
    assert results[0].shortage == 2
    assert results[0].selected == []


def test_draw_rejects_categories_from_a_different_bgg_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_randomizer_lookup(monkeypatch, [])

    with pytest.raises(game_randomizers.RandomizerCategoryNotFoundError):
        game_randomizers.draw(
            None,
            telegram_id=1,
            game_id=5,
            category_ids=[999],
            player_count=2,
        )
