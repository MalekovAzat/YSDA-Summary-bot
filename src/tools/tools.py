from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

def build_inline_keyboard(buttons: List[InlineKeyboardButton], row_width: int = 2) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for button in buttons:
        row.append(button)
        if len(row) == row_width:
            rows.append(row)
            row = []
    if row:  # добавляем оставшиеся кнопки
        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)