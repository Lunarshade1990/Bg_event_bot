from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from aiogram.exceptions import TelegramAPIError

from bot.app.handlers.meetups import (
    _delete_creation_messages,
    _format_actor_display_name,
    _format_create_meetup_confirmation,
    _format_creator_participation_notification,
    _format_game_suggestion_lines,
    _format_group_meetup_card,
    _format_meetup_details,
    _get_creation_ephemeral_message_ids,
    _get_creation_message_ids,
    _parse_chat_id,
    _parse_meetup_game_vote_callback,
    _show_suggestion_source_prompt,
    _start_private_chat_meetup_creation,
    change_games_page,
    finish_suggesting_meetup_games,
    receive_meetup_date,
    skip_game_selection,
    toggle_game_selection,
    toggle_meetup_game_vote,
)
from bot.app.keyboards.meetups import (
    get_group_meetup_keyboard,
    get_meetups_list_keyboard,
    get_meetups_menu_keyboard,
    get_suggestion_games_keyboard,
    get_suggestion_owner_keyboard,
)


def test_meetups_menu_has_separate_upcoming_and_archive_buttons() -> None:
    keyboard = get_meetups_menu_keyboard()
    labels = {button.text for row in keyboard.keyboard for button in row}

    assert "Запланированные встречи" in labels
    assert "Архив встреч" in labels
    assert "Список встреч" not in labels


def test_meetups_list_keyboard_switches_category_and_preserves_item_context() -> None:
    upcoming_keyboard = get_meetups_list_keyboard(
        [
            {
                "id": 42,
                "scheduled_at": "2026-10-08T18:00:00+00:00",
                "capacity_total": 4,
                "participants": [],
            }
        ],
    )
    archive_keyboard = get_meetups_list_keyboard([], archive=True)

    assert upcoming_keyboard.inline_keyboard[0][0].callback_data == "meetup:42:upcoming"
    assert upcoming_keyboard.inline_keyboard[-1][0].callback_data == "meetup_list:archive"
    assert archive_keyboard.inline_keyboard[-1][0].callback_data == "meetup_list:upcoming"


def test_group_meetup_keyboard_includes_game_suggestion_action() -> None:
    keyboard = get_group_meetup_keyboard(meetup_id=42, is_joined=False)

    assert keyboard.inline_keyboard[-1][0].text == "🎲 Предложить игру"
    assert keyboard.inline_keyboard[-1][0].callback_data == "meetup_suggest:42"


def test_meetup_game_vote_callback_parser_validates_both_ids() -> None:
    assert _parse_meetup_game_vote_callback("meetup_game_vote:42:7") == (42, 7)
    assert _parse_meetup_game_vote_callback("meetup_game_vote:0:7") is None
    assert _parse_meetup_game_vote_callback("meetup_game_vote:42:nope") is None
    assert _parse_meetup_game_vote_callback("meetup_game_vote:42:7:extra") is None


@pytest.mark.asyncio
async def test_meetup_game_vote_callback_saves_vote_and_refreshes_card(monkeypatch) -> None:
    class VotingBackend(FakeBackendAPIClient):
        async def get_meetup(self, meetup_id: int):
            assert meetup_id == 42
            return {
                "telegram_chat_id": -1001,
                "telegram_message_id": 111,
            }

        async def toggle_meetup_game_vote(
            self,
            meetup_id: int,
            *,
            user_id: int,
            game_id: int,
        ):
            assert (meetup_id, user_id, game_id) == (42, 1, 7)
            return {
                "game_suggestion_votes": [
                    {"game_id": 7, "voters": [{"user_id": 1}]},
                ],
            }

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", VotingBackend)
    monkeypatch.setattr("bot.app.handlers.meetups.Message", SimpleNamespace)
    refresh_card = AsyncMock()
    monkeypatch.setattr(
        "bot.app.handlers.meetups._refresh_group_meetup_card",
        refresh_card,
    )
    message = SimpleNamespace(
        chat=SimpleNamespace(type="supergroup", id=-1001),
        message_id=111,
        photo=[],
    )
    callback = SimpleNamespace(
        data="meetup_game_vote:42:7",
        message=message,
        bot=SimpleNamespace(),
        from_user=SimpleNamespace(
            id=100,
            username="voter",
            first_name="Voter",
            last_name=None,
        ),
        answer=AsyncMock(),
    )
    await toggle_meetup_game_vote(callback)
    refresh_card.assert_awaited_once()
    refreshed_meetup = refresh_card.await_args.args[1]
    assert refreshed_meetup["game_suggestion_votes"][0]["voters"] == [{"user_id": 1}]
    assert refresh_card.await_args.kwargs["has_photo"] is False
    callback.answer.assert_awaited_once_with("Голос учтён.")


def test_suggestion_source_keyboard_keeps_meetup_creator_first() -> None:
    keyboard = get_suggestion_owner_keyboard(
        [
            {"user_id": 1, "username": "creator", "display_name": "Creator"},
            {"user_id": 2, "username": "player", "display_name": "Player"},
        ]
    )

    assert keyboard.inline_keyboard[0][0].text == "@creator"
    assert keyboard.inline_keyboard[1][0].text == "@player"


def test_suggestion_game_keyboard_keeps_suggestion_controls() -> None:
    keyboard = get_suggestion_games_keyboard(
        [{"id": 1, "title": "Arcs"}],
        {1},
        page=1,
        has_more=True,
    )
    buttons = [button for row in keyboard.inline_keyboard for button in row]

    assert buttons[0].text == "✅ Arcs"
    assert buttons[0].callback_data == "meetup_suggest_toggle:1"
    assert buttons[1].callback_data == "meetup_suggest_page:0"
    assert buttons[2].callback_data == "meetup_suggest_page:2"
    assert buttons[3].callback_data == "meetup_suggest_done"
    assert buttons[-2].callback_data == "meetup_suggest_back"
    assert buttons[-1].callback_data == "meetup_suggest_cancel"


@pytest.mark.asyncio
async def test_suggestion_prompt_is_sent_to_user_private_chat() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    state = DummyState()

    await _show_suggestion_source_prompt(
        bot=bot,
        chat_id=12345,
        state=state,
        meetup={"id": 42, "status": "planned"},
        profile={"id": 9, "telegram_id": 12345},
        card_has_photo=True,
    )

    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.kwargs["chat_id"] == 12345
    assert state.data["meetup_id"] == 42
    assert state.data["card_has_photo"] is True


def _suggestion_flow_state(*, collection_owner_user_id: int) -> "DummyState":
    state = DummyState()
    state.data = {
        "selected_game_ids": [7],
        "selected_games": [{"id": 7, "title": "Catan <Deluxe>"}],
        "meetup_id": 42,
        "proposer_user_id": 9,
        "proposer_telegram_id": 900,
        "collection_owner_user_id": collection_owner_user_id,
        "card_has_photo": False,
    }
    return state


def _suggestion_callback(monkeypatch):
    monkeypatch.setattr("bot.app.handlers.meetups.Message", SimpleNamespace)
    message = SimpleNamespace(edit_text=AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock())
    return (
        SimpleNamespace(
            bot=bot,
            message=message,
            answer=AsyncMock(),
        ),
        bot,
        message,
    )


def _saved_suggestion_meetup() -> dict:
    return {
        "id": 42,
        "scheduled_at": "2026-10-08T18:00:00+00:00",
        "telegram_chat_id": -1001,
        "telegram_message_id": 111,
        "game_suggestions": [
            {
                "proposer_user_id": 9,
                "username": "recommender",
                "display_name": "Recommender",
                "games": [{"id": 7, "title": "Catan <Deluxe>"}],
            }
        ],
    }


@pytest.mark.asyncio
async def test_foreign_collection_suggestion_notifies_collection_owner(monkeypatch) -> None:
    saved_meetup = _saved_suggestion_meetup()

    class SuggestionBackend(FakeBackendAPIClient):
        async def suggest_meetup_games(self, *args, **kwargs):
            return saved_meetup

        async def get_user(self, user_id: int):
            assert user_id == 12
            return {"telegram_id": 1200}

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SuggestionBackend)
    monkeypatch.setattr(
        "bot.app.handlers.meetups._refresh_group_meetup_card",
        AsyncMock(),
    )
    callback, bot, message = _suggestion_callback(monkeypatch)

    await finish_suggesting_meetup_games(
        callback,
        _suggestion_flow_state(collection_owner_user_id=12),
    )

    bot.send_message.assert_awaited_once()
    notification = bot.send_message.await_args.kwargs
    assert notification["chat_id"] == 1200
    assert "@recommender рекомендует" in notification["text"]
    assert "Catan &lt;Deluxe&gt;" in notification["text"]
    assert "08.10.2026" in notification["text"]
    assert message.edit_text.await_args.args[0] == "Предложение добавлено к встрече."
    callback.answer.assert_awaited_once_with("Предложение добавлено.")


@pytest.mark.asyncio
async def test_own_collection_suggestion_does_not_notify_owner(monkeypatch) -> None:
    saved_meetup = _saved_suggestion_meetup()

    class SuggestionBackend(FakeBackendAPIClient):
        async def suggest_meetup_games(self, *args, **kwargs):
            return saved_meetup

        async def get_user(self, user_id: int):
            raise AssertionError("The proposer must not be notified about their own collection.")

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SuggestionBackend)
    monkeypatch.setattr(
        "bot.app.handlers.meetups._refresh_group_meetup_card",
        AsyncMock(),
    )
    callback, bot, message = _suggestion_callback(monkeypatch)

    await finish_suggesting_meetup_games(
        callback,
        _suggestion_flow_state(collection_owner_user_id=9),
    )

    bot.send_message.assert_not_awaited()
    assert message.edit_text.await_args.args[0] == "Предложение добавлено к встрече."
    callback.answer.assert_awaited_once_with("Предложение добавлено.")


@pytest.mark.asyncio
async def test_failed_collection_owner_lookup_keeps_suggestion_and_warns_proposer(
    monkeypatch,
) -> None:
    saved_meetup = _saved_suggestion_meetup()

    class SuggestionBackend(FakeBackendAPIClient):
        async def suggest_meetup_games(self, *args, **kwargs):
            return saved_meetup

        async def get_user(self, user_id: int):
            raise httpx.ConnectError("Backend unavailable")

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SuggestionBackend)
    refresh = AsyncMock()
    monkeypatch.setattr("bot.app.handlers.meetups._refresh_group_meetup_card", refresh)
    callback, bot, message = _suggestion_callback(monkeypatch)

    await finish_suggesting_meetup_games(
        callback,
        _suggestion_flow_state(collection_owner_user_id=12),
    )

    refresh.assert_awaited_once()
    bot.send_message.assert_not_awaited()
    assert message.edit_text.await_args.args[0] == (
        "Предложение добавлено, но владельца коллекции уведомить не удалось."
    )
    callback.answer.assert_awaited_once_with(
        "Предложение добавлено, но владельца коллекции уведомить не удалось.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_failed_telegram_delivery_keeps_suggestion_and_warns_proposer(
    monkeypatch,
) -> None:
    saved_meetup = _saved_suggestion_meetup()

    class SuggestionBackend(FakeBackendAPIClient):
        async def suggest_meetup_games(self, *args, **kwargs):
            return saved_meetup

        async def get_user(self, user_id: int):
            return {"telegram_id": 1200}

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SuggestionBackend)
    refresh = AsyncMock()
    monkeypatch.setattr("bot.app.handlers.meetups._refresh_group_meetup_card", refresh)
    callback, bot, message = _suggestion_callback(monkeypatch)
    bot.send_message.side_effect = TelegramAPIError(
        method=SimpleNamespace(),
        message="bot was blocked by the user",
    )

    await finish_suggesting_meetup_games(
        callback,
        _suggestion_flow_state(collection_owner_user_id=12),
    )

    refresh.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    assert message.edit_text.await_args.args[0] == (
        "Предложение добавлено, но владельца коллекции уведомить не удалось."
    )
    callback.answer.assert_awaited_once_with(
        "Предложение добавлено, но владельца коллекции уведомить не удалось.",
        show_alert=True,
    )


def test_game_suggestion_lines_include_user_and_escape_game_titles() -> None:
    lines = _format_game_suggestion_lines(
        [
            {
                "username": "player",
                "display_name": "Player",
                "games": [{"title": "Catan <Deluxe>"}, {"title": "Azul"}],
            }
        ]
    )

    assert lines == ["@player предлагает игры: Catan &lt;Deluxe&gt;, Azul"]


def test_format_meetup_details_escapes_user_content() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": "Играем в _Catan_ и *Azul* <test>",
            "participants": [
                {
                    "telegram_id": 100,
                    "display_name": "Anna & Co",
                    "username": None,
                    "status": "joined",
                }
            ],
        }
    )

    assert text.startswith("<b>в понедельник в 19:30</b>"), text
    assert "Играем в _Catan_ и *Azul* <test>" not in text
    assert "Играем в _Catan_ и *Azul* &lt;test&gt;" in text
    assert "Anna & Co" not in text
    assert "Anna &amp; Co" in text


def test_format_create_meetup_confirmation_escapes_comment() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment="Catan <Azul> & tea",
    )

    assert "Дата: <code>15.06.2026 19:30</code>" in text
    assert "Игроков: 4" in text
    assert "Catan &lt;Azul&gt; &amp; tea" in text


def test_format_create_meetup_confirmation_omits_empty_comment() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment=None,
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text


def test_format_create_meetup_confirmation_includes_selected_games() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment=None,
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text


def test_get_creation_message_ids_deduplicates_extra_message_ids() -> None:
    message_ids = _get_creation_message_ids(
        {"creation_message_ids": [10, 11, 10, "bad"]},
        11,
        12,
    )

    assert message_ids == [10, 11, 12]


def test_get_creation_ephemeral_message_ids_deduplicates_extra_ids() -> None:
    message_ids = _get_creation_ephemeral_message_ids(
        {"creation_ephemeral_message_ids": [20, 21, 20, "bad"]},
        21,
        22,
    )

    assert message_ids == [20, 21, 22]


@pytest.mark.asyncio
async def test_delete_creation_messages_deletes_ephemeral_messages_for_recipient() -> None:
    bot = SimpleNamespace(
        delete_message=AsyncMock(),
        delete_ephemeral_message=AsyncMock(),
    )

    await _delete_creation_messages(
        bot,
        chat_id=-1001,
        message_ids=[10],
        receiver_user_id=123,
        ephemeral_message_ids=[20],
    )

    bot.delete_message.assert_awaited_once_with(chat_id=-1001, message_id=10)
    bot.delete_ephemeral_message.assert_awaited_once_with(
        chat_id=-1001,
        receiver_user_id=123,
        ephemeral_message_id=20,
    )


def test_format_meetup_details_omits_empty_comment() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        }
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text


def test_format_group_meetup_card_omits_empty_comment() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        }
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text
    assert text.startswith("<b>в понедельник в 19:30</b>"), text


def test_format_group_meetup_card_includes_selected_games() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text
    assert text.startswith("<b>Catan в понедельник в 19:30</b>"), text


def test_format_group_meetup_card_keeps_game_suggestions() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
            "game_suggestions": [
                {
                    "username": "player",
                    "display_name": "Player",
                    "games": [{"title": "Catan"}, {"title": "Azul"}],
                }
            ],
        }
    )

    assert "@player предлагает игры: Catan, Azul" in text


def test_format_meetup_details_keeps_game_suggestions() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
            "game_suggestions": [
                {
                    "username": "player",
                    "display_name": "Player",
                    "games": [{"title": "Catan"}, {"title": "Azul"}],
                }
            ],
        }
    )

    assert "@player предлагает игры: Catan, Azul" in text


def test_format_meetup_details_includes_selected_games() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text
    assert text.startswith("<b>Catan в понедельник в 19:30</b>"), text


def test_parse_chat_id_accepts_positive_and_negative_values() -> None:
    assert _parse_chat_id("meetup_chat_select:123", "meetup_chat_select") == 123
    assert _parse_chat_id("meetup_chat_select:-100123", "meetup_chat_select") == -100123
    assert _parse_chat_id("meetup_chat_select:abc", "meetup_chat_select") is None
    assert _parse_chat_id("other_prefix:123", "meetup_chat_select") is None


def test_get_meetup_chat_selection_keyboard_truncates_long_titles() -> None:
    from bot.app.keyboards.meetups import get_meetup_chat_selection_keyboard

    keyboard = get_meetup_chat_selection_keyboard(
        [
            {"telegram_chat_id": -1001, "title": "A" * 100},
            {"telegram_chat_id": -1002, "title": "Short name"},
        ]
    )

    labels = [row[0].text for row in keyboard.inline_keyboard]

    assert labels[0].endswith("...")
    assert len(labels[0]) <= 50
    assert labels[1] == "Short name"


class DummyState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def clear(self) -> None:
        self.data.clear()
        self.state = None

    async def update_data(self, **data) -> None:
        self.data.update(data)

    async def set_state(self, state) -> None:
        self.state = state

    async def get_data(self) -> dict:
        return self.data


class DummyMessage:
    def __init__(self):
        self.chat = SimpleNamespace(type="private", id=-1)
        self.from_user = SimpleNamespace(
            id=123,
            username="testuser",
            first_name="Test",
            last_name="User",
        )
        self.last_answer = None

    async def answer(self, text: str, parse_mode: str | None = None, reply_markup=None):
        self.last_answer = SimpleNamespace(text=text, reply_markup=reply_markup, message_id=1)
        return self.last_answer

    async def edit_text(self, text: str, parse_mode: str | None = None, reply_markup=None):
        self.last_edited = SimpleNamespace(text=text, reply_markup=reply_markup)
        return self.last_edited


class FakeBackendAPIClient:
    async def sync_telegram_user(self, **kwargs):
        return {}

    async def get_user_by_telegram_id(self, telegram_id: int):
        return {"id": 1}


@pytest.mark.asyncio
async def test_start_private_chat_meetup_creation_single_chat_sets_group_mode(monkeypatch) -> None:
    class SingleChatBackend(FakeBackendAPIClient):
        async def list_telegram_chat_memberships(self, user_id: int):
            return [
                {"telegram_chat_id": -1001, "telegram_thread_id": 111, "title": "Test Chat"},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SingleChatBackend)

    state = DummyState()
    message = DummyMessage()

    await _start_private_chat_meetup_creation(message, state)

    assert state.state is not None
    assert state.data["telegram_chat_id"] == -1001
    assert state.data["telegram_thread_id"] == 111
    assert state.data["group_mode"] is True
    assert message.last_answer is not None
    assert "Укажи дату" in message.last_answer.text


@pytest.mark.asyncio
async def test_start_private_chat_meetup_creation_multiple_chats_shows_selection(
    monkeypatch,
) -> None:
    class MultipleChatsBackend(FakeBackendAPIClient):
        async def list_telegram_chat_memberships(self, user_id: int):
            return [
                {"telegram_chat_id": -1001, "telegram_thread_id": 111, "title": "First Chat"},
                {"telegram_chat_id": -1002, "telegram_thread_id": 222, "title": "Second Chat"},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", MultipleChatsBackend)

    state = DummyState()
    message = DummyMessage()

    await _start_private_chat_meetup_creation(message, state)

    assert state.state is not None
    assert "waiting_for_chat_selection" in str(state.state)
    assert message.last_answer is not None
    assert "Выбери чат" in message.last_answer.text
    assert len(message.last_answer.reply_markup.inline_keyboard) == 2


@pytest.mark.asyncio
async def test_skip_game_selection_moves_to_capacity() -> None:
    state = DummyState()
    message = DummyMessage()
    # Simulate a callback query-like object
    callback = SimpleNamespace(
        data="meetup_game_skip",
        message=message,
        from_user=SimpleNamespace(id=123),
    )

    await skip_game_selection(callback, state)

    assert state.state is not None
    assert "waiting_for_capacity" in str(state.state)
    assert hasattr(message, "last_edited")
    assert "Сколько всего игроков" in message.last_edited.text


@pytest.mark.asyncio
async def test_toggle_game_selection_keeps_all_games_on_current_page(monkeypatch) -> None:
    monkeypatch.setattr(
        "bot.app.handlers.meetups.BackendAPIClient",
        lambda: pytest.fail("Toggling a game should use the preloaded letter map."),
    )
    edit_prompt = AsyncMock()
    monkeypatch.setattr("bot.app.handlers.meetups._edit_creation_prompt", edit_prompt)
    games = [{"id": index, "title": f"Arcs {index}", "max_players": 4} for index in range(1, 10)]
    state = DummyState()
    state.data = {
        "letters_map": {"A": games},
        "current_game_letter": "A",
        "current_game_page": 0,
        "available_games": {str(game["id"]): game for game in games[:8]},
        "selected_game_ids": [],
        "selected_games": [],
    }
    callback = SimpleNamespace(
        data="meetup_game_toggle:1",
        answer=AsyncMock(),
    )

    await toggle_game_selection(callback, state)

    keyboard = edit_prompt.await_args.kwargs["reply_markup"]
    buttons = [row[0] for row in keyboard.inline_keyboard[:8]]
    assert [button.text for button in buttons] == [
        "✅ Arcs 1",
        "Arcs 2",
        "Arcs 3",
        "Arcs 4",
        "Arcs 5",
        "Arcs 6",
        "Arcs 7",
        "Arcs 8",
    ]
    assert [button.callback_data for button in buttons] == [
        f"meetup_game_toggle:{index}" for index in range(1, 9)
    ]
    assert state.data["selected_game_ids"] == [1]
    assert state.data["selected_games"] == [games[0]]

    callback.data = "meetup_game_toggle:1"
    await toggle_game_selection(callback, state)

    keyboard = edit_prompt.await_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].text == "Arcs 1"
    assert state.data["selected_game_ids"] == []
    assert state.data["selected_games"] == []


@pytest.mark.asyncio
async def test_change_games_page_uses_preloaded_letter_map(monkeypatch) -> None:
    monkeypatch.setattr(
        "bot.app.handlers.meetups.BackendAPIClient",
        lambda: pytest.fail("Changing pages should use the preloaded letter map."),
    )
    edit_prompt = AsyncMock()
    monkeypatch.setattr("bot.app.handlers.meetups._edit_creation_prompt", edit_prompt)
    games = [{"id": index, "title": f"Arcs {index}"} for index in range(1, 11)]
    state = DummyState()
    state.data = {
        "letters_map": {"A": games},
        "current_game_letter": "A",
        "selected_game_ids": [],
    }
    callback = SimpleNamespace(
        data="meetup_game_page:1",
        answer=AsyncMock(),
    )

    await change_games_page(callback, state)

    keyboard = edit_prompt.await_args.kwargs["reply_markup"]
    game_buttons = [
        row[0]
        for row in keyboard.inline_keyboard
        if row[0].callback_data.startswith("meetup_game_toggle:")
    ]
    assert [button.callback_data for button in game_buttons] == [
        "meetup_game_toggle:9",
        "meetup_game_toggle:10",
    ]
    assert state.data["current_game_page"] == 1
    navigation_buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("meetup_game_page:")
    ]
    assert [button.callback_data for button in navigation_buttons] == ["meetup_game_page:0"]


@pytest.mark.asyncio
async def test_receive_meetup_date_builds_letters(monkeypatch) -> None:
    class GamesBackend(FakeBackendAPIClient):
        async def list_games(self, owner_id: int, game_type: str, limit: int, offset: int):
            return [
                {"id": 1, "title": "Arcs", "min_players": 1, "max_players": 4},
                {"id": 2, "title": "Iss Vanguard", "min_players": 1, "max_players": 4},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", GamesBackend)

    state = DummyState()
    message = DummyMessage()
    message.text = "15.06.2099 19:30"
    message.message_id = 1

    await receive_meetup_date(message, state)

    data = await state.get_data()
    assert "letters_map" in data
    assert set(data["letters_map"].keys()) == {"A", "I"}
    assert hasattr(message, "last_edited") or hasattr(message, "last_answer")


def test_format_actor_display_name_prefers_username() -> None:
    assert _format_actor_display_name({"username": "boardgamer", "display_name": "Board Gamer"}) == (
        "@boardgamer"
    )


def test_format_actor_display_name_escapes_display_name() -> None:
    assert _format_actor_display_name({"username": None, "display_name": "Anna & Co"}) == (
        "Anna &amp; Co"
    )


def test_format_creator_participation_notification_join() -> None:
    text = _format_creator_participation_notification(
        meetup={
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 6,
            "comment": "Играем в _Catan_",
            "participants": [{"telegram_id": 1}, {"telegram_id": 2}],
        },
        actor_display="@alice",
        action="join",
    )

    assert "<b>@alice</b> записался на встречу." in text
    assert "Участников: 2/6" in text
    assert "Играем в _Catan_" in text


def test_format_creator_participation_notification_leave_omits_comment() -> None:
    text = _format_creator_participation_notification(
        meetup={
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        actor_display="Bob",
        action="leave",
    )

    assert "<b>Bob</b> отписался от встречи." in text
    assert "Участников: 0/4" in text
    assert "Комментарий:" not in text
