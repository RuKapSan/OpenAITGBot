from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType, BufferedInputFile
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import TEST_MODE, logger
from ..services.payment_service import create_session, get_session, delete_session
from ..services.telegram_service import download_image
from ..services.openai_service import generate_image

generation_router = Router()

@generation_router.message(ImageGenerationStates.waiting_for_prompt, F.content_type == ContentType.TEXT)
async def handle_prompt(message: Message, state: FSMContext, bot: Bot):
    """Обработка текстового промпта"""
    prompt = message.text
    await state.update_data(prompt=prompt)
    
    data = await state.get_data()
    images = data.get('images', [])
    images_count = len(images)
    
    # Создаем сессию
    session_id = create_session(message.from_user.id, images, prompt)
    await state.update_data(session_id=session_id)
    
    if TEST_MODE:
        # Тестовый режим - сразу на генерацию
        await message.answer(
            "🧪 <b>ТЕСТОВЫЙ РЕЖИМ</b>\n"
            "Оплата пропущена для тестирования!",
            parse_mode="HTML"
        )
        await process_generation(message, state, session_id, message.bot)
    else:
        # Обычный режим - переходим к оплате
        await state.set_state(ImageGenerationStates.waiting_for_payment)
        
        # Импортируем и вызываем функцию создания инвойса
        from ..services.payment_service import create_invoice
        await create_invoice(message, session_id, prompt, images_count)

@generation_router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    session_id = payment.invoice_payload
    
    await message.answer("✅ Оплата получена!")
    await process_generation(message, state, session_id, message.bot)

async def process_generation(message: Message, state: FSMContext, session_id: str, bot):
    """Выполнить генерацию изображения"""
    session = get_session(session_id)
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
                img_bytes = await download_image(bot, file_id)
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
        delete_session(session_id)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при генерации: {e}")
        await message.answer(
            "❌ Произошла ошибка при генерации.\n"
            f"Ошибка: {str(e)}"
        )

@generation_router.message(ImageGenerationStates.waiting_for_prompt)
async def wrong_content_prompt(message: Message):
    """Обработка неверного типа контента при ожидании промпта"""
    await message.answer(
        "❌ Пожалуйста, отправьте текстовое описание"
    )