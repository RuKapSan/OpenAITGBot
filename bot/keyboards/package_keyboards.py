"""
Клавиатуры для выбора пакетов генераций
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import PACKAGES


def get_package_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с пакетами генераций"""
    buttons = []
    
    # Эмоджи для пакетов
    emojis = ["🎯", "🎨", "🎪", "🚀"]
    
    # Создаем кнопки из конфигурации
    for i, package in enumerate(PACKAGES):
        size = package["size"]
        price = package["price"]
        discount = package["discount"]
        
        # Формируем текст кнопки
        if size == 1:
            text = f"{emojis[i]} {size} генерация - {price} Stars"
        else:
            text = f"{emojis[i]} {size} генераций - {price} Stars"
        
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"package:{size}:{price}"
        )])
    
    # Добавляем кнопку отмены
    buttons.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="package:cancel"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_generation")]
    ])