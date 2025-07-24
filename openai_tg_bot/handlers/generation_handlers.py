from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType, BufferedInputFile
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import TEST_MODE, logger, GENERATION_PRICE, MAX_PROMPT_LENGTH, OPENAI_CONCURRENT_LIMIT
from ..services.payment_service import payment_service
from ..services.telegram_service import download_image
from ..services.openai_service import generate_image, GenerationError, generation_semaphore
from .. import messages

generation_router = Router()


@generation_router.message(ImageGenerationStates.waiting_for_prompt, F.content_type == ContentType.TEXT)
async def handle_prompt(message: Message, state: FSMContext):
    """Обработка текстового промпта"""
    prompt = message.text.strip()
    
    # Валидация промпта
    if len(prompt) > MAX_PROMPT_LENGTH:
        await message.answer(
            messages.PROMPT_TOO_LONG.format(
                max_length=MAX_PROMPT_LENGTH,
                current_length=len(prompt)
            )
        )
        return
    
    if len(prompt) < 3:
        await message.answer(messages.PROMPT_TOO_SHORT)
        return
    
    await state.update_data(prompt=prompt)
    
    data = await state.get_data()
    images = data.get('images', [])
    images_count = len(images)
    
    try:
        # Создаем сессию
        session_id = await payment_service.create_session(
            message.from_user.id, 
            images, 
            prompt
        )
        await state.update_data(session_id=session_id)
        
        if TEST_MODE:
            # Тестовый режим - сразу на генерацию
            await message.answer(
                messages.TEST_MODE_MESSAGE,
                parse_mode="HTML"
            )
            await process_generation(message, state, session_id)
        else:
            # Обычный режим - переходим к оплате
            await state.set_state(ImageGenerationStates.waiting_for_payment)
            await payment_service.create_invoice(
                message, 
                session_id, 
                prompt, 
                images_count
            )
    
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка создания сессии: {e}")
        await message.answer(messages.ERROR_SESSION_CREATE)

@generation_router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    session_id = payment.invoice_payload
    payment_charge_id = payment.telegram_payment_charge_id
    
    # Сохраняем информацию о платеже
    await payment_service.save_payment(
        session_id=session_id,
        user_id=message.from_user.id,
        payment_charge_id=payment_charge_id,
        amount=GENERATION_PRICE
    )
    
    await message.answer(messages.PAYMENT_RECEIVED)
    await process_generation(message, state, session_id)


async def process_generation(message: Message, state: FSMContext, session_id: str):
    """Выполнить генерацию изображения"""
    session = await payment_service.get_session(session_id)
    if not session:
        await message.answer(messages.ERROR_SESSION_NOT_FOUND)
        await state.clear()
        return
    
    # Проверяем очередь
    queue_position = OPENAI_CONCURRENT_LIMIT - generation_semaphore._value
    if queue_position > 0:
        await message.answer(
            messages.GENERATION_QUEUED.format(position=queue_position)
        )
    else:
        await message.answer(messages.GENERATION_STARTED)
    
    try:
        # Скачиваем изображения если есть
        input_images = []
        if session['images']:
            for file_id in session['images']:
                img_bytes = await download_image(message.bot, file_id)
                input_images.append(img_bytes)
        
        # Генерируем изображение
        result_image = await generate_image(session['prompt'], input_images)
        
        # Отправляем результат
        footer = (
            messages.GENERATION_SUCCESS_FOOTER_TEST 
            if TEST_MODE 
            else messages.GENERATION_SUCCESS_FOOTER_PAID
        )
        
        await message.answer_photo(
            photo=BufferedInputFile(result_image, filename="generated.png"),
            caption=messages.GENERATION_SUCCESS.format(
                prompt=session['prompt'],
                footer=footer
            ),
            parse_mode="HTML"
        )
        
        # Очищаем сессию
        await payment_service.delete_session(session_id)
        await state.clear()
        
    except GenerationError as e:
        # Показываем пользователю понятное сообщение об ошибке
        logger.error(f"Ошибка генерации для сессии {session_id}: {e}")
        
        if not TEST_MODE and session.get('payment_charge_id'):
            await message.answer(f"❌ {str(e)}")
            await payment_service.process_payment_error(
                message.bot,
                message,
                session_id,
                e
            )
        else:
            await message.answer(f"❌ {str(e)}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при генерации для сессии {session_id}: {e}")
        
        # Обрабатываем ошибку с автоматическим возвратом
        if not TEST_MODE and session.get('payment_charge_id'):
            await payment_service.process_payment_error(
                message.bot,
                message,
                session_id,
                e
            )
        else:
            await message.answer(messages.ERROR_GENERATION_GENERIC)
        
        await state.clear()

@generation_router.message(ImageGenerationStates.waiting_for_prompt)
async def wrong_content_prompt(message: Message):
    """Обработка неверного типа контента при ожидании промпта"""
    await message.answer(messages.WRONG_CONTENT_PROMPT)