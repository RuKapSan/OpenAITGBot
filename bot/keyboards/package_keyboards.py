"""
Клавиатуры для выбора пакетов генераций
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_package_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с пакетами генераций"""
    buttons = [
        [InlineKeyboardButton(
            text="🎯 1 генерация - 20 Stars",
            callback_data="package:1:20"
        )],
        [InlineKeyboardButton(
            text="🎨 5 генераций - 90 Stars (скидка 10%)",
            callback_data="package:5:90"
        )],
        [InlineKeyboardButton(
            text="🎪 10 генераций - 160 Stars (скидка 20%)",
            callback_data="package:10:160"
        )],
        [InlineKeyboardButton(
            text="🚀 20 генераций - 280 Stars (скидка 30%)",
            callback_data="package:20:280"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="package:cancel"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_generation")]
    ])