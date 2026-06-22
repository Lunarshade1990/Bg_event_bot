import random

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.app.services.backend_api import BackendAPIClient
from bot.app.services.game_service import load_owned_games
from bot.app.states.random_game import RandomGameState

router = Router(name="games")

REROLL_CALLBACK = "REROLL_CALLBACK"
DONE_CALLBACK = "DONE_CALLBACK"


@router.message(Command("random_game"))
async def get_random_game_from_user_list(message: Message, state: FSMContext):
    await state.set_state(RandomGameState.waiting_for_players_count)
    await message.answer("Сколько человек будет играть?")


@router.message(RandomGameState.waiting_for_players_count)
async def get_players_count(message: Message, state: FSMContext):
    player_count = 0
    try:
        if message.text is not None:
            player_count = int(message.text)
    except ValueError:
        await message.answer("Не смог распознать ответ. Нужно ввести число")
        return

    if player_count < 1:
        await message.answer(
            "Число игроков не может быть меньше 1. Введите число больше 0"
        )
        return

    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    backend_client = BackendAPIClient()
    try:
        profile = await backend_client.get_user_by_telegram_id(user.id)
    except httpx.HTTPError:
        await message.answer(text="Не удалось связаться с backend API.")
        return True

    if profile is None:
        await message.answer(
            text="Я не нашел твой профиль. Нажми /start, чтобы синхронизироваться с backend."
        )
        return True

    games_list = await load_owned_games(profile["id"])
    filtered_games = [
        game_dict
        for game_dict in games_list
        if game_dict["display_max_players"] >= player_count
        and game_dict["display_min_players"] <= player_count
        and not game_dict["game"]["has_campaign"]
    ]
    if not filtered_games:
        await state.clear()
        await message.answer("Не нашлось подходящих игр под такое количество игроков.")
        return

    random_game = random.choice(filtered_games)
    title = random_game["game"]["title"]
    await state.update_data(games_list=filtered_games)
    await state.update_data(random_games=[title])
    await state.update_data(player_count=player_count)
    await message.answer(
        f"Ваша игра: {title}!",
        reply_markup=keyboard(),
    )


@router.callback_query(F.data == REROLL_CALLBACK)
async def reroll_game(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    random_games = list(data.get("random_games", []))
    filtered_games = data.get("games_list")

    await callback.answer()
    if filtered_games:
        filtered_games = list(filtered_games)
        if len(filtered_games) == len(random_games):
            await state.clear()
            await callback.message.edit_text("Больше вариантов нет :(\nНачните с начала")
            return
        while True:
            selected_game = random.choice(filtered_games)
            if selected_game["game"]["title"] not in random_games:
                break
        title = selected_game["game"]["title"]
        random_games.append(title)
        await state.update_data(random_games=random_games)
        await callback.message.edit_text(f"Ваша игра: {title}!", reply_markup=keyboard())
        return

    await callback.answer("Список игр пуст!")


@router.callback_query(F.data == DONE_CALLBACK)
async def done(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Приятной игры! 🎲")
    await callback.answer()


def keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Выбрать другую игру", callback_data=REROLL_CALLBACK
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Играем!", callback_data=DONE_CALLBACK
                )
            ]
        ]
    )
