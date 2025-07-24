from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates

command_router = Router()

@command_router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "🎨 Добро пожаловать в бот генерации изображений!\n\n"
        "Этот бот может:\n"
        "• Генерировать новые изображения по текстовому описанию\n"
        "• Редактировать и комбинировать ваши фотографии\n\n"
        "💰 Стоимость: 20 Stars за генерацию\n\n"
        "Команды:\n"
        "/generate - Начать генерацию\n"
        "/help - Подробная инструкция"
    )

@command_router.message(Command("help"))
async def help_command(message: Message):
    """Подробная инструкция"""
    await message.answer(
        "📖 <b>Как использовать бот:</b>\n\n"
        "1️⃣ Нажмите /generate\n"
        "2️⃣ Отправьте от 1 до 3 изображений (опционально)\n"
        "3️⃣ Напишите текстовое описание того, что хотите получить\n"
        "4️⃣ Оплатите 20 Stars\n"
        "5️⃣ Получите результат!\n\n"
        "<b>Примеры промптов:</b>\n"
        "• \"Сделай фото в стиле аниме\"\n"
        "• \"Добавь космический фон\"\n"
        "• \"Объедини эти фото в одну композицию\"\n"
        "• \"Нарисуй кота в костюме астронавта\"\n\n"
        "<i>💡 Чем подробнее описание, тем лучше результат!</i>",
        parse_mode="HTML"
    )

@command_router.message(Command("generate"))
async def generate_command(message: Message, state: FSMContext):
    """Начать процесс генерации"""
    await state.clear()
    await state.set_state(ImageGenerationStates.waiting_for_images)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить и перейти к описанию ➡️", callback_data="skip_images")]
    ])
    
    await message.answer(
        "🖼 Отправьте от 1 до 3 изображений для редактирования.\n\n"
        "Или нажмите кнопку ниже, чтобы сгенерировать изображение с нуля:",
        reply_markup=keyboard
    )