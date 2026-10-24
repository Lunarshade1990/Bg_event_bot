from html import escape

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.app.keyboards.main_menu import (
    RANDOMIZER_COMPONENTS_BUTTON_TEXT,
    RANDOMIZERS_MENU_TEXT,
    get_randomizers_menu_keyboard,
)
from bot.app.keyboards.meetups import (
    get_game_group_keyboard,
    get_games_list_keyboard,
    get_letters_keyboard,
)
from bot.app.services.backend_api import BackendAPIClient
from bot.app.states.random_game import RandomizerStates

router = Router(name="randomizer")
MENU_TEXT = RANDOMIZER_COMPONENTS_BUTTON_TEXT
GAME_GROUP_CALLBACK = "rz:gamegroup"
GAME_LETTER_CALLBACK = "rz:gameletter"
GAME_PAGE_CALLBACK = "rz:gamepage"
GAME_PICK_CALLBACK = "rz:pickgame"
PAGE_SIZE = 8
OPTIONS_PAGE_SIZE = 20


@router.message(F.text == RANDOMIZERS_MENU_TEXT)
async def open_randomizers_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рандомайзеры:", reply_markup=get_randomizers_menu_keyboard())


@router.message(F.text == MENU_TEXT)
async def open_randomizer(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.chat.type != "private":
        await message.answer("Рандомайзер доступен только в личном чате с ботом.")
        return

    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return
    try:
        profile = await BackendAPIClient().get_user_by_telegram_id(user.id)
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    if profile is None:
        await message.answer("Нажми /start, чтобы создать профиль.")
        return
    if not (profile.get("bgg_username") or "").strip():
        await message.answer(
            "Сначала укажи ник BGG через «Импорт из BGG». "
            "Рандомайзер общий для всех, кто использует один и тот же ник BGG."
        )
        return

    await _start_game_picker(message, state, user.id)


@router.message(F.text.in_({"Отмена", "/cancel"}))
async def cancel_randomizer_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.")


@router.callback_query(F.message.chat.type != "private")
async def reject_group_randomizer_callback(callback: CallbackQuery) -> None:
    await callback.answer("Рандомайзер работает только в личном чате с ботом.", show_alert=True)


@router.callback_query(F.data.startswith(f"{GAME_GROUP_CALLBACK}:"))
async def select_randomizer_game_group(callback: CallbackQuery, state: FSMContext) -> None:
    index = _callback_int(callback.data, 2)
    data = await state.get_data()
    groups = data.get("randomizer_letter_groups") or []
    if index is None or index >= len(groups):
        await callback.answer("Неизвестная группа букв.", show_alert=True)
        return
    await state.update_data(randomizer_current_group=index)
    await _show_randomizer_letters(callback, state, list(groups[index]))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{GAME_LETTER_CALLBACK}:"))
async def select_randomizer_game_letter(callback: CallbackQuery, state: FSMContext) -> None:
    letter = (callback.data or "").split(":", 2)[2]
    data = await state.get_data()
    letters_map = data.get("randomizer_letters_map") or {}
    games = letters_map.get(letter)
    if not games:
        await callback.answer("Игры на эту букву не найдены.", show_alert=True)
        return
    await state.update_data(
        randomizer_current_letter=letter,
        randomizer_game_page=0,
    )
    await _show_randomizer_games_page(callback, state, letter, 0)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{GAME_PAGE_CALLBACK}:"))
async def change_randomizer_game_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = _callback_int(callback.data, 2)
    data = await state.get_data()
    letter = data.get("randomizer_current_letter")
    if page is None or not letter:
        await callback.answer("Некорректная страница игр.", show_alert=True)
        return
    await state.update_data(randomizer_game_page=page)
    await _show_randomizer_games_page(callback, state, letter, page)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{GAME_PICK_CALLBACK}:"))
async def select_randomizer_game(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    if game_id is None:
        await callback.answer("Некорректная игра.", show_alert=True)
        return
    await state.update_data(game_id=game_id, selected_category_ids=[])
    await _render_game_menu(callback, state, game_id)


@router.callback_query(F.data == "rz:picker:back")
async def back_to_randomizer_letters(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    letter = data.get("randomizer_current_letter")
    if letter:
        await state.update_data(randomizer_current_letter=None)
    group_index = data.get("randomizer_current_group")
    if group_index is not None:
        groups = data.get("randomizer_letter_groups") or []
        groups = groups if group_index < len(groups) else []
        letters = list(groups[group_index]) if groups else []
    else:
        letters = sorted((data.get("randomizer_letters_map") or {}).keys())
    await _show_randomizer_letters(callback, state, letters)
    await callback.answer()


@router.callback_query(F.data == "rz:pickergroups")
async def back_to_randomizer_groups(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    groups = data.get("randomizer_letter_groups") or []
    await _show_randomizer_groups(callback, groups)
    await callback.answer()


@router.callback_query(F.data == "rz:backpicker")
async def back_to_randomizer_game_page(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    letter = data.get("randomizer_current_letter")
    page = data.get("randomizer_game_page", 0)
    if not letter:
        await _show_randomizer_picker(callback, state)
    else:
        await _show_randomizer_games_page(callback, state, letter, page)
    await callback.answer()


@router.callback_query(F.data == "rz:picker:cancel")
async def cancel_randomizer_picker(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit_or_answer(callback, "Выбор игры отменён.")
    await callback.answer()


@router.callback_query(F.data.startswith("rz:manage:"))
async def open_category_list(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    if game_id is None:
        await callback.answer("Некорректная игра.", show_alert=True)
        return
    await _render_category_list(callback, game_id)


@router.callback_query(F.data.startswith("rz:cat:"))
async def open_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    await _render_category_details(callback, int(parts[2]), int(parts[3]))


@router.callback_query(F.data.startswith("rz:catpage:"))
async def open_category_page(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or not all(part.isdigit() for part in parts[2:]):
        await callback.answer("Некорректная страница вариантов.", show_alert=True)
        return
    game_id, category_id, offset = map(int, parts[2:])
    await _render_category_details(callback, game_id, category_id, offset=offset)


@router.callback_query(F.data.startswith("rz:addcat:"))
async def start_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    if game_id is None:
        await callback.answer("Некорректная игра.", show_alert=True)
        return
    await state.update_data(game_id=game_id)
    await state.set_state(RandomizerStates.waiting_for_category_name)
    await _edit_or_answer(callback, "Как назвать поле? Например: «Нация» или «Сценарий».")
    await callback.answer()


@router.message(RandomizerStates.waiting_for_category_name)
async def receive_category_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не должно быть пустым. Введи его ещё раз.")
        return
    if len(name) > 100:
        await message.answer("Название поля не должно превышать 100 символов.")
        return
    await state.update_data(category_name=name)
    await state.set_state(RandomizerStates.waiting_for_category_count)
    await message.answer("Сколько вариантов выбирать? Введи число или напиши «по числу игроков».")


@router.message(RandomizerStates.waiting_for_category_count)
async def receive_category_count(message: Message, state: FSMContext) -> None:
    draw_count = _parse_draw_count(message.text)
    if draw_count is False:
        await message.answer(
            "Введи положительное число не больше 100 или напиши «по числу игроков»."
        )
        return
    data = await state.get_data()
    user = message.from_user
    if user is None or not data.get("game_id"):
        await state.clear()
        await message.answer("Не удалось продолжить настройку. Начни заново из меню.")
        return
    try:
        category = await BackendAPIClient().create_game_randomizer_category(
            telegram_id=user.id,
            game_id=data["game_id"],
            name=data["category_name"],
            draw_count=draw_count,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            await state.set_state(RandomizerStates.waiting_for_category_name)
            await message.answer("Такое поле уже есть. Введи другое название.")
            return
        await message.answer(f"Не удалось создать поле: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    await state.update_data(category_id=category["id"])
    await state.set_state(RandomizerStates.waiting_for_options)
    await message.answer(
        "Теперь пришли варианты одним сообщением, по одному на строку. "
        "Пустые строки будут проигнорированы. Чтобы добавить их позже, отправь «-»."
    )


@router.callback_query(F.data.startswith("rz:addopts:"))
async def start_add_options(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    await state.update_data(game_id=int(parts[2]), category_id=int(parts[3]))
    await state.set_state(RandomizerStates.waiting_for_options)
    await _edit_or_answer(
        callback,
        "Пришли варианты одним сообщением, по одному на строку. "
        "Запятые внутри названий допускаются.",
    )
    await callback.answer()


@router.message(RandomizerStates.waiting_for_options)
async def receive_options(message: Message, state: FSMContext) -> None:
    user = message.from_user
    data = await state.get_data()
    if user is None or not data.get("game_id") or not data.get("category_id"):
        await state.clear()
        await message.answer("Не удалось продолжить настройку. Начни заново из меню.")
        return
    raw_text = (message.text or "").strip()
    if raw_text == "-":
        await state.clear()
        await message.answer("Поле сохранено без новых вариантов.")
        return
    values = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not values:
        await message.answer("Не нашёл вариантов. Отправь каждый вариант с новой строки.")
        return
    if len(values) > 100:
        await message.answer("За раз можно добавить не больше 100 вариантов.")
        return
    if any(len(value) > 500 for value in values):
        await message.answer("Каждый вариант должен быть не длиннее 500 символов.")
        return
    try:
        await BackendAPIClient().add_game_randomizer_options(
            telegram_id=user.id,
            game_id=data["game_id"],
            category_id=data["category_id"],
            values=values,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось добавить варианты: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    game_id = data["game_id"]
    await state.clear()
    await message.answer(f"Добавлено вариантов: {len(values)}.")
    await _send_category_list(message, user.id, game_id)


@router.callback_query(F.data.startswith("rz:rename:"))
async def start_rename_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    await state.update_data(game_id=int(parts[2]), category_id=int(parts[3]))
    await state.set_state(RandomizerStates.waiting_for_category_rename)
    await _edit_or_answer(callback, "Введи новое название поля.")
    await callback.answer()


@router.message(RandomizerStates.waiting_for_category_rename)
async def receive_category_rename(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer("Название должно содержать от 1 до 100 символов.")
        return
    await _update_category_from_message(
        message,
        state,
        {"name": name},
        "Название поля обновлено.",
    )


@router.callback_query(F.data.startswith("rz:count:"))
async def start_update_count(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    await state.update_data(game_id=int(parts[2]), category_id=int(parts[3]))
    await state.set_state(RandomizerStates.waiting_for_category_count_update)
    await _edit_or_answer(
        callback,
        "Сколько вариантов выбирать? Введи число или напиши «по числу игроков».",
    )
    await callback.answer()


@router.message(RandomizerStates.waiting_for_category_count_update)
async def receive_count_update(message: Message, state: FSMContext) -> None:
    draw_count = _parse_draw_count(message.text)
    if draw_count is False:
        await message.answer(
            "Введи положительное число не больше 100 или напиши «по числу игроков»."
        )
        return
    await _update_category_from_message(
        message,
        state,
        {"draw_count": draw_count, "update_draw_count": True},
        "Количество вариантов обновлено.",
    )


@router.callback_query(F.data.startswith("rz:delcat:"))
async def delete_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    game_id, category_id = int(parts[2]), int(parts[3])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=f"rz:confirmdelcat:{game_id}:{category_id}",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"rz:cat:{game_id}:{category_id}",
                ),
            ]
        ]
    )
    await _edit_or_answer(callback, "Удалить поле вместе со всеми вариантами?", keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("rz:confirmdelcat:"))
async def confirm_delete_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    game_id, category_id = int(parts[2]), int(parts[3])
    try:
        await BackendAPIClient().delete_game_randomizer_category(
            telegram_id=callback.from_user.id,
            game_id=game_id,
            category_id=category_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    await _render_category_list(callback, game_id)
    await callback.answer("Поле удалено.")


@router.callback_query(F.data.startswith("rz:option:"))
async def open_option(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 6 or not all(part.isdigit() for part in parts[2:]):
        await callback.answer("Некорректный вариант.", show_alert=True)
        return
    game_id, category_id, option_id, offset = map(int, parts[2:])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Изменить",
                    callback_data=f"rz:editopt:{game_id}:{category_id}:{option_id}:{offset}",
                ),
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=f"rz:delopt:{game_id}:{category_id}:{option_id}:{offset}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="← К полю",
                    callback_data=f"rz:catpage:{game_id}:{category_id}:{offset}",
                )
            ],
        ]
    )
    await _edit_or_answer(callback, "Что сделать с этим вариантом?", keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("rz:editopt:"))
async def start_edit_option(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 6 or not all(part.isdigit() for part in parts[2:]):
        await callback.answer("Некорректный вариант.", show_alert=True)
        return
    game_id, category_id, option_id, offset = map(int, parts[2:])
    await state.update_data(
        game_id=game_id,
        category_id=category_id,
        option_id=option_id,
        option_offset=offset,
    )
    await state.set_state(RandomizerStates.waiting_for_option_update)
    await _edit_or_answer(callback, "Введи новый текст варианта.")
    await callback.answer()


@router.message(RandomizerStates.waiting_for_option_update)
async def receive_option_update(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value or len(value) > 500:
        await message.answer("Вариант должен содержать от 1 до 500 символов.")
        return
    data = await state.get_data()
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return
    try:
        await BackendAPIClient().update_game_randomizer_option(
            telegram_id=user.id,
            game_id=data["game_id"],
            category_id=data["category_id"],
            option_id=data["option_id"],
            value=value,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось изменить вариант: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    await state.clear()
    await message.answer("Вариант обновлён.")
    await _send_category_details(
        message,
        user.id,
        data["game_id"],
        data["category_id"],
        offset=data.get("option_offset", 0),
    )


@router.callback_query(F.data.startswith("rz:delopt:"))
async def delete_option(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 6 or not all(part.isdigit() for part in parts[2:]):
        await callback.answer("Некорректный вариант.", show_alert=True)
        return
    game_id, category_id, option_id, offset = map(int, parts[2:])
    try:
        await BackendAPIClient().delete_game_randomizer_option(
            telegram_id=callback.from_user.id,
            game_id=game_id,
            category_id=category_id,
            option_id=option_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    await _render_category_details(callback, game_id, category_id, offset=offset)
    await callback.answer("Вариант удалён.")


@router.callback_query(F.data.startswith("rz:drawmenu:"))
async def open_draw_menu(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    if game_id is None:
        await callback.answer("Некорректная игра.", show_alert=True)
        return
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    categories = config["categories"]
    if not categories:
        await callback.answer("Сначала добавь хотя бы одно поле.", show_alert=True)
        return
    selected_ids = [item["id"] for item in categories]
    await state.update_data(game_id=game_id, selected_category_ids=selected_ids)
    await _render_draw_menu(callback, config, selected_ids)
    await callback.answer()


@router.callback_query(F.data.startswith("rz:toggle:"))
async def toggle_draw_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректное поле.", show_alert=True)
        return
    game_id, category_id = int(parts[2]), int(parts[3])
    data = await state.get_data()
    selected = set(data.get("selected_category_ids", []))
    if category_id in selected:
        selected.remove(category_id)
    else:
        selected.add(category_id)
    selected_ids = sorted(selected)
    await state.update_data(selected_category_ids=selected_ids)
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    await _render_draw_menu(callback, config, selected_ids)
    await callback.answer()


@router.callback_query(F.data.startswith("rz:draw:"))
async def execute_draw(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    if game_id is None or not selected_ids:
        await callback.answer("Выбери хотя бы одно поле.", show_alert=True)
        return
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    selected_categories = [
        category for category in config["categories"] if category["id"] in selected_ids
    ]
    if any(category["draw_count"] is None for category in selected_categories):
        await state.update_data(game_id=game_id)
        await state.set_state(RandomizerStates.waiting_for_draw_players_count)
        await _edit_or_answer(callback, "Сколько человек будет играть?")
        await callback.answer()
        return
    await _run_draw(callback, state, game_id, selected_ids, None)
    await callback.answer()


@router.message(RandomizerStates.waiting_for_draw_players_count)
async def receive_draw_players_count(message: Message, state: FSMContext) -> None:
    try:
        player_count = int((message.text or "").strip())
        if not 1 <= player_count <= 100:
            raise ValueError
    except ValueError:
        await message.answer("Введи число игроков от 1 до 100.")
        return
    data = await state.get_data()
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return
    try:
        result = await BackendAPIClient().draw_game_randomizer(
            telegram_id=user.id,
            game_id=data["game_id"],
            category_ids=data["selected_category_ids"],
            player_count=player_count,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось провести розыгрыш: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    await state.set_state(None)
    await message.answer(
        _format_draw_result(result), reply_markup=_get_result_keyboard(data["game_id"])
    )


@router.callback_query(F.data.startswith("rz:reroll:"))
async def reroll(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids")
    if game_id is None or not selected_ids:
        await callback.answer("Сначала выбери категории для розыгрыша.", show_alert=True)
        return
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    selected_categories = [
        category for category in config["categories"] if category["id"] in selected_ids
    ]
    if any(category["draw_count"] is None for category in selected_categories):
        await state.update_data(game_id=game_id)
        await state.set_state(RandomizerStates.waiting_for_draw_players_count)
        await _edit_or_answer(callback, "Сколько человек будет играть?")
        await callback.answer()
        return
    await _run_draw(callback, state, game_id, selected_ids, None)
    await callback.answer()


@router.callback_query(F.data.startswith("rz:backgame:"))
async def back_to_game_menu(callback: CallbackQuery, state: FSMContext) -> None:
    game_id = _callback_int(callback.data, 2)
    if game_id is None:
        await callback.answer("Некорректная игра.", show_alert=True)
        return
    await _render_game_menu(callback, state, game_id)


async def _start_game_picker(
    message: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    client = BackendAPIClient()
    games: list[dict] = []
    offset = 0
    try:
        while True:
            batch = await client.list_randomizer_games(
                telegram_id=telegram_id,
                limit=100,
                offset=offset,
            )
            games.extend(batch)
            if len(batch) < 100:
                break
            offset += 100
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось загрузить игры: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    letters_map: dict[str, list[dict]] = {}
    for game in games:
        title = (game.get("title") or "").strip()
        if title and title[0].isalpha():
            letters_map.setdefault(title[0].upper(), []).append(game)
    letters = sorted(letters_map)
    if not letters:
        await message.answer(
            "Не нашёл игр в этой коллекции. Сначала импортируй коллекцию через BGG."
        )
        return

    groups = [letters[index : index + 6] for index in range(0, len(letters), 6)]
    await state.update_data(
        randomizer_letters_map=letters_map,
        randomizer_letter_groups=groups if len(letters) > 5 else [],
        randomizer_current_group=None,
        randomizer_current_letter=None,
        randomizer_game_page=0,
    )
    await _show_randomizer_picker_message(message, letters, groups)


async def _show_randomizer_picker_message(
    message: Message,
    letters: list[str],
    groups: list[list[str]],
) -> None:
    if len(letters) > 5:
        keyboard = get_game_group_keyboard(
            groups,
            set(),
            callback_prefix=GAME_GROUP_CALLBACK,
            include_done=False,
            include_skip=False,
            back_callback_data="rz:picker:cancel",
        )
        await message.answer("Выбери диапазон букв:", reply_markup=keyboard)
        return
    keyboard = get_letters_keyboard(
        letters,
        callback_prefix=GAME_LETTER_CALLBACK,
        include_done=False,
        include_skip=False,
        back_callback_data="rz:picker:cancel",
    )
    await message.answer("Выбери первую букву:", reply_markup=keyboard)


async def _show_randomizer_picker(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    letters_map = data.get("randomizer_letters_map") or {}
    groups = data.get("randomizer_letter_groups") or []
    letters = sorted(letters_map)
    if len(letters) > 5:
        await _show_randomizer_groups(callback, groups)
        return
    await _show_randomizer_letters(callback, state, letters)


async def _show_randomizer_groups(
    callback: CallbackQuery,
    groups: list[list[str]],
) -> None:
    keyboard = get_game_group_keyboard(
        groups,
        set(),
        callback_prefix=GAME_GROUP_CALLBACK,
        include_done=False,
        include_skip=False,
        back_callback_data="rz:picker:cancel",
    )
    await _edit_or_answer(callback, "Выбери диапазон букв:", keyboard)


async def _show_randomizer_letters(
    callback: CallbackQuery,
    state: FSMContext,
    letters: list[str],
) -> None:
    data = await state.get_data()
    back_callback_data = (
        "rz:pickergroups"
        if data.get("randomizer_current_group") is not None
        else "rz:picker:cancel"
    )
    keyboard = get_letters_keyboard(
        letters,
        callback_prefix=GAME_LETTER_CALLBACK,
        include_done=False,
        include_skip=False,
        back_callback_data=back_callback_data,
    )
    await _edit_or_answer(callback, "Выбери первую букву:", keyboard)


async def _show_randomizer_games_page(
    callback: CallbackQuery,
    state: FSMContext,
    letter: str,
    page: int,
) -> None:
    data = await state.get_data()
    all_games = (data.get("randomizer_letters_map") or {}).get(letter, [])
    start = page * PAGE_SIZE
    games = all_games[start : start + PAGE_SIZE]
    has_more = start + PAGE_SIZE < len(all_games)
    await _edit_or_answer(
        callback,
        f"Игры на букву {letter} (страница {page + 1}):",
        get_games_list_keyboard(
            games,
            set(),
            page,
            has_more,
            callback_prefix=GAME_PICK_CALLBACK,
            page_callback_prefix=GAME_PAGE_CALLBACK,
            show_selection=False,
            include_done=False,
            include_skip=False,
            back_callback_data="rz:picker:back",
        ),
    )


async def _render_game_menu(
    callback: CallbackQuery,
    state: FSMContext,
    game_id: int,
) -> None:
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    categories = config["categories"]
    buttons = []
    if categories:
        buttons.append(
            [InlineKeyboardButton(text="🎲 Разыграть", callback_data=f"rz:drawmenu:{game_id}")]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="⚙️ Настроить поля",
                callback_data=f"rz:manage:{game_id}",
            )
        ]
    )
    buttons.append([InlineKeyboardButton(text="← К выбору игр", callback_data="rz:backpicker")])
    category_summary = "\n".join(
        f"• {escape(item['name'])}: {len(item['options'])} вариантов" for item in categories[:20]
    )
    if len(categories) > 20:
        category_summary += f"\n… и ещё {len(categories) - 20} полей."
    text = f"<b>{escape(config['game']['title'])}</b>"
    if category_summary:
        text += f"\n\nПоля:\n{category_summary}"
    else:
        text += "\n\nПоля ещё не настроены."
    await _edit_or_answer(
        callback,
        text,
        InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await state.update_data(game_id=game_id)
    await callback.answer()


async def _render_category_list(callback: CallbackQuery, game_id: int) -> None:
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    await _show_category_list(callback, config)
    await callback.answer()


async def _send_category_list(message: Message, telegram_id: int, game_id: int) -> None:
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=telegram_id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось загрузить поля: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    keyboard, text = _category_list_keyboard(config)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_category_list(callback: CallbackQuery, config: dict) -> None:
    keyboard, text = _category_list_keyboard(config)
    await _edit_or_answer(callback, text, keyboard, parse_mode="HTML")


def _category_list_keyboard(config: dict) -> tuple[InlineKeyboardMarkup, str]:
    game = config["game"]
    categories = config["categories"]
    rows = [
        [
            InlineKeyboardButton(
                text=f"{category['name'][:40]} ({len(category['options'])})",
                callback_data=f"rz:cat:{game['id']}:{category['id']}",
            )
        ]
        for category in categories
    ]
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Добавить поле",
                    callback_data=f"rz:addcat:{game['id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← К игре",
                    callback_data=f"rz:backgame:{game['id']}",
                )
            ],
        ]
    )
    return (
        InlineKeyboardMarkup(inline_keyboard=rows),
        f"<b>{escape(game['title'])}</b>\nВыбери поле или добавь новое:",
    )


async def _render_category_details(
    callback: CallbackQuery,
    game_id: int,
    category_id: int,
    *,
    offset: int = 0,
) -> None:
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    category = next(
        (item for item in config["categories"] if item["id"] == category_id),
        None,
    )
    if category is None:
        await callback.answer("Поле не найдено.", show_alert=True)
        return
    max_offset = max(
        0,
        ((len(category["options"]) - 1) // OPTIONS_PAGE_SIZE) * OPTIONS_PAGE_SIZE,
    )
    await _show_category_details(
        callback,
        game_id,
        category,
        offset=min(offset, max_offset),
    )
    await callback.answer()


async def _send_category_details(
    message: Message,
    telegram_id: int,
    game_id: int,
    category_id: int,
    *,
    offset: int = 0,
) -> None:
    try:
        config = await BackendAPIClient().get_game_randomizer(
            telegram_id=telegram_id,
            game_id=game_id,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось загрузить поле: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    category = next(
        (item for item in config["categories"] if item["id"] == category_id),
        None,
    )
    if category is None:
        await message.answer("Поле не найдено.")
        return
    max_offset = max(
        0,
        ((len(category["options"]) - 1) // OPTIONS_PAGE_SIZE) * OPTIONS_PAGE_SIZE,
    )
    keyboard, text = _category_details_keyboard(
        game_id,
        category,
        offset=min(offset, max_offset),
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_category_details(
    callback: CallbackQuery,
    game_id: int,
    category: dict,
    *,
    offset: int,
) -> None:
    keyboard, text = _category_details_keyboard(game_id, category, offset=offset)
    await _edit_or_answer(callback, text, keyboard, parse_mode="HTML")


def _category_details_keyboard(
    game_id: int,
    category: dict,
    *,
    offset: int,
) -> tuple[InlineKeyboardMarkup, str]:
    category_id = category["id"]
    options = category["options"]
    count_text = (
        "по числу игроков" if category["draw_count"] is None else str(category["draw_count"])
    )
    rows = [
        [
            InlineKeyboardButton(
                text=f"📝 {option['value'][:55]}",
                callback_data=(f"rz:option:{game_id}:{category_id}:{option['id']}:{offset}"),
            )
        ]
        for option in options[offset : offset + OPTIONS_PAGE_SIZE]
    ]
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Добавить варианты",
                    callback_data=f"rz:addopts:{game_id}:{category_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Название",
                    callback_data=f"rz:rename:{game_id}:{category_id}",
                ),
                InlineKeyboardButton(
                    text=f"🔢 Количество: {count_text}"[:64],
                    callback_data=f"rz:count:{game_id}:{category_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить поле",
                    callback_data=f"rz:delcat:{game_id}:{category_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← К списку полей",
                    callback_data=f"rz:manage:{game_id}",
                )
            ],
        ]
    )
    if len(options) > OPTIONS_PAGE_SIZE:
        page_buttons: list[InlineKeyboardButton] = []
        if offset > 0:
            page_buttons.append(
                InlineKeyboardButton(
                    text="← Варианты",
                    callback_data=(
                        f"rz:catpage:{game_id}:{category_id}:{max(0, offset - OPTIONS_PAGE_SIZE)}"
                    ),
                )
            )
        if offset + OPTIONS_PAGE_SIZE < len(options):
            page_buttons.append(
                InlineKeyboardButton(
                    text="Варианты →",
                    callback_data=(
                        f"rz:catpage:{game_id}:{category_id}:{offset + OPTIONS_PAGE_SIZE}"
                    ),
                )
            )
        if page_buttons:
            rows.insert(-1, page_buttons)
    text = (
        f"<b>{escape(category['name'])}</b>\nВыбирается: {escape(count_text)}"
        f"\nВариантов: {len(options)}"
    )
    displayed_options: list[str] = []
    page_options = options[offset : offset + OPTIONS_PAGE_SIZE]
    for index, option in enumerate(page_options, start=offset + 1):
        line = f"{index}. {escape(option['value'][:100])}"
        candidate = f"{text}\n\n" + "\n".join([*displayed_options, line])
        if len(candidate) > 3800:
            displayed_options.append("… список длинный, показаны не все варианты.")
            break
        displayed_options.append(line)
    if len(options) > OPTIONS_PAGE_SIZE:
        displayed_options.append(
            f"Страница {offset // OPTIONS_PAGE_SIZE + 1} из "
            f"{(len(options) + OPTIONS_PAGE_SIZE - 1) // OPTIONS_PAGE_SIZE}."
        )
    if displayed_options:
        text = f"{text}\n\n" + "\n".join(displayed_options)
    return InlineKeyboardMarkup(inline_keyboard=rows), text


async def _render_draw_menu(
    callback: CallbackQuery,
    config: dict,
    selected_ids: list[int],
) -> None:
    game_id = config["game"]["id"]
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'☑️' if category['id'] in selected_ids else '▫️'} "
                f"{category['name'][:48]} ({len(category['options'])})",
                callback_data=f"rz:toggle:{game_id}:{category['id']}",
            )
        ]
        for category in config["categories"]
    ]
    rows.extend(
        [
            [InlineKeyboardButton(text="🎲 Рандомизировать", callback_data=f"rz:draw:{game_id}")],
            [InlineKeyboardButton(text="← К игре", callback_data=f"rz:backgame:{game_id}")],
        ]
    )
    await _edit_or_answer(
        callback,
        f"<b>{escape(config['game']['title'])}</b>\n"
        "Отметь поля, которые нужно разыграть. Все выбраны по умолчанию.",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


async def _run_draw(
    callback: CallbackQuery,
    state: FSMContext,
    game_id: int,
    category_ids: list[int],
    player_count: int | None,
) -> None:
    try:
        result = await BackendAPIClient().draw_game_randomizer(
            telegram_id=callback.from_user.id,
            game_id=game_id,
            category_ids=category_ids,
            player_count=player_count,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return
    await state.update_data(game_id=game_id, selected_category_ids=category_ids)
    await _edit_or_answer(
        callback,
        _format_draw_result(result),
        _get_result_keyboard(game_id),
        parse_mode="HTML",
    )


def _format_draw_result(result: dict) -> str:
    lines = [f"<b>{escape(result['game']['title'])}</b>"]
    for category in result["categories"]:
        category_lines = [f"\n<b>{escape(category['category_name'])}</b>"]
        if category["shortage"]:
            category_lines.append(
                f"Не хватает вариантов: нужно {category['requested_count']}, "
                f"есть {category['available_count']}."
            )
        else:
            category_lines.extend(f"• {escape(value)}" for value in category["selected"])
        if len("\n".join([*lines, *category_lines])) > 3800:
            lines.append("\nОстальные результаты не помещаются в одно сообщение.")
            break
        lines.extend(category_lines)
    return "\n".join(lines)


def _get_result_keyboard(game_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Повторить", callback_data=f"rz:reroll:{game_id}")],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"rz:backgame:{game_id}")],
        ]
    )


async def _update_category_from_message(
    message: Message,
    state: FSMContext,
    payload: dict,
    success_text: str,
) -> None:
    data = await state.get_data()
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return
    try:
        await BackendAPIClient().update_game_randomizer_category(
            telegram_id=user.id,
            game_id=data["game_id"],
            category_id=data["category_id"],
            payload=payload,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось обновить поле: {_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return
    await state.clear()
    await message.answer(success_text)
    await _send_category_details(
        message,
        user.id,
        data["game_id"],
        data["category_id"],
    )


async def _edit_or_answer(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = None,
) -> None:
    message = callback.message
    if message is None:
        return
    await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)


def _callback_int(data: str | None, part_index: int) -> int | None:
    if data is None:
        return None
    parts = data.split(":")
    if len(parts) <= part_index or not parts[part_index].isdigit():
        return None
    return int(parts[part_index])


def _parse_draw_count(text: str | None) -> int | None | bool:
    value = (text or "").strip().lower()
    if value in {"по числу игроков", "по количеству игроков"}:
        return None
    try:
        count = int(value)
    except ValueError:
        return False
    return count if 1 <= count <= 100 else False


def _error_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
    except ValueError:
        return exc.response.text or "Ошибка backend API."
    return str(payload.get("detail", exc.response.text))
