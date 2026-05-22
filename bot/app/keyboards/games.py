from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MY_GAMES_PAGE_SIZE = 5
MY_GAMES_CALLBACK_PREFIX = "my_games"


def get_my_games_keyboard(
    *,
    offset: int,
    page_size: int = MY_GAMES_PAGE_SIZE,
    has_next_page: bool,
) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []

    if offset > 0:
        previous_offset = max(offset - page_size, 0)
        buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"{MY_GAMES_CALLBACK_PREFIX}:{previous_offset}",
            )
        )

    if has_next_page:
        next_offset = offset + page_size
        buttons.append(
            InlineKeyboardButton(
                text="Вперед →",
                callback_data=f"{MY_GAMES_CALLBACK_PREFIX}:{next_offset}",
            )
        )

    if not buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=[buttons])
