"""
Клавиатуры для выбора пакетов генераций
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from bot.config import PACKAGES


def get_generation_word(count: int) -> str:
    """Возвращает правильную форму слова 'генерация' в зависимости от числа"""
    if count % 10 == 1 and count % 100 != 11:
        return "генерация"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "генерации"
    else:
        return "генераций"


def get_package_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с пакетами генераций"""
    buttons = []
    
    # Эмоджи для пакетов
    emojis = ["🎯", "🎨", "🎪", "🚀"]
    
    # Создаем кнопки из конфигурации
    for i, package in enumerate(PACKAGES):
        size = package["size"]
        price = package["price"]
        
        # Выбираем emoji с проверкой границ
        emoji = emojis[i] if i < len(emojis) else "💎"
        
        # Формируем текст кнопки
        generation_word = get_generation_word(size)
        text = f"{emoji} {size} {generation_word} - {price} Stars"
        
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


def get_reset_keyboard() -> ReplyKeyboardMarkup:
    """Создает обычную клавиатуру с кнопкой сброса"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Начать заново")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_retry_inline_keyboard() -> InlineKeyboardMarkup:
    """Создает inline клавиатуру с кнопкой повтора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Попробовать снова",
            callback_data="retry_payment"
        )]
    ])