import asyncio
import logging
import base64
import json
from io import BytesIO
from typing import List, Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message, 
    PreCheckoutQuery, 
    LabeledPrice,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    ContentType,
    FSInputFile,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import aiohttp
from openai import AsyncOpenAI
from PIL import Image
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо установить BOT_TOKEN и OPENAI_API_KEY в .env файле")

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# OpenAI клиент
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Состояния для FSM
class ImageGenStates(StatesGroup):
    waiting_for_images = State()
    waiting_for_prompt = State()
    waiting_for_payment = State()

# Временное хранилище данных сессий (вместо БД)
generation_sessions = {}

# Цена генерации
GENERATION_PRICE = 20  # Stars

# Тестовый режим (set to True to skip payment)
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

@router.message(Command("start"))
async def cmd_start(message: Message):
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

@router.message(Command("help"))
async def cmd_help(message: Message):
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

@router.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext):
    """Начать процесс генерации"""
    await state.clear()
    await state.set_state(ImageGenStates.waiting_for_images)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить и перейти к описанию ➡️", callback_data="skip_images")]
    ])
    
    await message.answer(
        "🖼 Отправьте от 1 до 3 изображений для редактирования.\n\n"
        "Или нажмите кнопку ниже, чтобы сгенерировать изображение с нуля:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "skip_images")
async def skip_images(callback: CallbackQuery, state: FSMContext):
    """Пропустить загрузку изображений"""
    await callback.answer()
    await state.set_state(ImageGenStates.waiting_for_prompt)
    await callback.message.edit_text(
        "✍️ Теперь опишите, какое изображение вы хотите получить.\n\n"
        "Чем подробнее описание, тем лучше результат!"
    )

@router.message(ImageGenStates.waiting_for_images, F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, state: FSMContext):
    """Обработка загруженных фото"""
    data = await state.get_data()
    images = data.get('images', [])
    
    # Получаем file_id самого большого размера фото
    photo = message.photo[-1]
    images.append(photo.file_id)
    
    await state.update_data(images=images)
    
    if len(images) >= 3:
        await state.set_state(ImageGenStates.waiting_for_prompt)
        await message.answer(
            f"✅ Загружено {len(images)} изображений (максимум).\n\n"
            "✍️ Теперь опишите, что вы хотите сделать с этими изображениями:"
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Продолжить с {len(images)} фото ➡️", 
                callback_data="continue_to_prompt"
            )]
        ])
        await message.answer(
            f"📸 Загружено {len(images)}/3 изображений.\n"
            "Можете отправить еще или продолжить:",
            reply_markup=keyboard
        )

@router.callback_query(F.data == "continue_to_prompt")
async def continue_to_prompt(callback: CallbackQuery, state: FSMContext):
    """Перейти к вводу промпта"""
    await callback.answer()
    await state.set_state(ImageGenStates.waiting_for_prompt)
    await callback.message.edit_text(
        "✍️ Отлично! Теперь опишите, что вы хотите сделать с этими изображениями:"
    )

@router.message(ImageGenStates.waiting_for_prompt, F.content_type == ContentType.TEXT)
async def handle_prompt(message: Message, state: FSMContext):
    """Обработка текстового промпта"""
    prompt = message.text
    await state.update_data(prompt=prompt)
    
    data = await state.get_data()
    images_count = len(data.get('images', []))
    
    # Создаем сессию
    session_id = f"{message.from_user.id}_{int(datetime.now().timestamp())}"
    generation_sessions[session_id] = {
        'user_id': message.from_user.id,
        'images': data.get('images', []),
        'prompt': prompt,
        'status': 'pending'
    }
    
    await state.update_data(session_id=session_id)
    
    if TEST_MODE:
        # Тестовый режим - сразу на генерацию
        await message.answer(
            "🧪 <b>ТЕСТОВЫЙ РЕЖИМ</b>\n"
            "Оплата пропущена для тестирования!",
            parse_mode="HTML"
        )
        await process_generation(message, state, session_id)
    else:
        # Обычный режим - запрос оплаты
        await state.set_state(ImageGenStates.waiting_for_payment)
        
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Генерация изображения",
            description=f"Промпт: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n"
                       f"Изображений: {images_count}",
            payload=session_id,
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(label="Генерация", amount=GENERATION_PRICE)
            ],
            photo_url="https://cdn-icons-png.flaticon.com/512/2779/2779775.png",
            photo_width=512,
            photo_height=512
        )

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение готовности принять платеж"""
    session_id = pre_checkout_query.invoice_payload
    
    if session_id not in generation_sessions:
        await bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=False,
            error_message="Сессия истекла. Пожалуйста, начните заново."
        )
        return
    
    await bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )

async def download_image(file_id: str) -> bytes:
    """Скачать изображение из Telegram"""
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as resp:
            return await resp.read()

async def generate_image(prompt: str, input_images: List[bytes] = None) -> bytes:
    """Генерация изображения через OpenAI API"""
    try:
        if input_images:
            # Редактирование с входными изображениями
            # Конвертируем изображения в base64
            base64_images = []
            for img_bytes in input_images:
                base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
            
            # Открываем изображения для редактирования
            files = []
            for i, img_bytes in enumerate(input_images):
                # Сохраняем временно для API
                temp_path = f"temp_image_{i}.png"
                with open(temp_path, 'wb') as f:
                    f.write(img_bytes)
                files.append(open(temp_path, 'rb'))
            
            try:
                response = await openai_client.images.edit(
                    model="gpt-image-1",
                    image=files[0] if len(files) == 1 else files,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="high",
                    background="auto"
                )
            finally:
                # Закрываем файлы и удаляем временные
                for i, f in enumerate(files):
                    f.close()
                    os.remove(f"temp_image_{i}.png")
        else:
            # Генерация с нуля
            response = await openai_client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                quality="high",
                output_format="jpeg"
            )
        
        # Получаем base64 изображение
        image_base64 = response.data[0].b64_json
        return base64.b64decode(image_base64)
        
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise

async def process_generation(message: Message, state: FSMContext, session_id: str):
    """Выполнить генерацию изображения"""
    session = generation_sessions.get(session_id)
    if not session:
        await message.answer("❌ Ошибка: сессия не найдена")
        return
    
    await message.answer(
        "✅ Начинаю генерацию изображения...\n"
        "🎨 Это может занять 30-60 секунд"
    )
    
    try:
        # Скачиваем изображения если есть
        input_images = []
        if session['images']:
            for file_id in session['images']:
                img_bytes = await download_image(file_id)
                input_images.append(img_bytes)
        
        # Генерируем изображение
        result_image = await generate_image(session['prompt'], input_images)
        
        # Отправляем результат
        await message.answer_photo(
            photo=BufferedInputFile(result_image, filename="generated.png"),
            caption=(
                f"✨ <b>Готово!</b>\n\n"
                f"<b>Промпт:</b> {session['prompt']}\n\n"
                f"<i>{'🧪 Тестовый режим' if TEST_MODE else 'Спасибо за покупку!'}</i>"
            ),
            parse_mode="HTML"
        )
        
        # Очищаем сессию
        generation_sessions.pop(session_id, None)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при генерации: {e}")
        await message.answer(
            "❌ Произошла ошибка при генерации.\n"
            f"Ошибка: {str(e)}"
        )

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    session_id = payment.invoice_payload
    
    await message.answer("✅ Оплата получена!")
    await process_generation(message, state, session_id)

@router.message(ImageGenStates.waiting_for_images)
async def wrong_content_images(message: Message):
    """Обработка неверного типа контента при ожидании изображений"""
    await message.answer(
        "❌ Пожалуйста, отправьте изображение или нажмите 'Пропустить'"
    )

@router.message(ImageGenStates.waiting_for_prompt)
async def wrong_content_prompt(message: Message):
    """Обработка неверного типа контента при ожидании промпта"""
    await message.answer(
        "❌ Пожалуйста, отправьте текстовое описание"
    )

async def main():
    """Главная функция"""
    # Регистрируем роутер
    dp.include_router(router)
    
    # Запускаем бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())