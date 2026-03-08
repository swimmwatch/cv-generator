import typing

from aiogram.types import InlineKeyboardButton

T = typing.TypeVar("T")


def get_paginated_list_keyboard(
    current_page: int,
    total_pages: int,
    items: typing.Iterable[T],
    item_title_getter: typing.Callable[[T], str],
    item_id_getter: typing.Callable[[T], str | int],
    item_prefix_callback: str,
    base_prefix: str,
):
    prev_page = current_page - 1
    if prev_page < 1:
        prev_page = total_pages

    next_page = current_page + 1
    if next_page > total_pages:
        next_page = 1

    keyboard = []

    items_btn = [
        [
            InlineKeyboardButton(
                text=item_title_getter(item),
                callback_data=f"{item_prefix_callback}{str(item_id_getter(item))}",
            )
        ]
        for item in items
    ]
    control_btn = [
        InlineKeyboardButton(text="<", callback_data=f"{base_prefix}{prev_page}"),
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data=" "),
        InlineKeyboardButton(text=">", callback_data=f"{base_prefix}{next_page}"),
    ]

    # do not add controls buttons if the list is empty
    if items_btn:
        keyboard.extend(items_btn)
        keyboard.append(control_btn)

    return keyboard
