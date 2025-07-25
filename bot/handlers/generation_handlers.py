from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType, BufferedInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import TEST_MODE, logger, GENERATION_PRICE, MAX_PROMPT_LENGTH, OPENAI_CONCURRENT_LIMIT, MAX_IMAGES_PER_REQUEST
from ..services import payment_service, balance_service
from ..services.telegram_service import download_image
from ..services.openai_service import generate_image, GenerationError, generation_semaphore
from ..services import queue_service
from ..keyboards.package_keyboards import get_package_keyboard
from .. import messages

generation_router = Router()


@generation_router.message(ImageGenerationStates.waiting_for_prompt, F.content_type == ContentType.PHOTO)
async def handle_photo_only(message: Message, state: FSMContext) -> None:
    """Обработка фото без текста в состоянии ожидания промпта"""
    data = await state.get_data()
    images = data.get('images', [])
    
    # Добавляем фото
    photo = message.photo[-1]
    images.append(photo.file_id)
    
    # Проверяем, есть ли caption (текст с фото)
    if message.caption:
        # Если есть текст - обрабатываем как полный запрос
        await state.update_data(images=images)
        await handle_prompt_with_data(message, state, message.caption)
    else:
        # Если текста нет - сохраняем фото и ждем текст
        await state.update_data(images=images)
        
        if len(images) >= MAX_IMAGES_PER_REQUEST:
            await message.answer(
                messages.IMAGES_MAX_REACHED.format(count=len(images))
            )
        else:
            await message.answer(
                f"📸 Загружено {len(images)}/{MAX_IMAGES_PER_REQUEST} изображений.\n\n✍️ Теперь отправьте текстовое описание:"
            )


async def handle_prompt_with_data(message: Message, state: FSMContext, prompt: str) -> None:
    """Общая логика обработки промпта с изображениями"""
    prompt = prompt.strip()
    
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
            # Проверяем баланс пользователя
            user_balance = await balance_service.get_balance(message.from_user.id)
            
            if user_balance > 0:
                # Есть баланс - списываем и генерируем
                success = await balance_service.deduct_balance(message.from_user.id, 1)
                if success:
                    await message.answer(
                        f"✅ Списана 1 генерация. Осталось: {user_balance - 1}"
                    )
                    await process_generation(message, state, session_id)
                else:
                    # Не удалось списать (параллельная транзакция?)
                    await message.answer("❌ Ошибка списания баланса. Попробуйте еще раз.")
                    await state.clear()
            else:
                # Нет баланса - показываем пакеты
                await state.set_state(ImageGenerationStates.choosing_package)
                await show_package_options(message)
    
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")
    except (AttributeError, TypeError, KeyError) as e:
        logger.error(f"Ошибка создания сессии: {e}")
        await message.answer(messages.ERROR_SESSION_CREATE)


@generation_router.message(ImageGenerationStates.waiting_for_prompt, F.content_type == ContentType.TEXT)
async def handle_prompt(message: Message, state: FSMContext) -> None:
    """Обработка текстового промпта"""
    await handle_prompt_with_data(message, state, message.text)


@generation_router.message(ImageGenerationStates.waiting_for_prompt)
async def wrong_content_type(message: Message) -> None:
    """Обработка неверного типа контента"""
    await message.answer(
        "❌ Пожалуйста, отправьте текстовое описание или фотографию с описанием."
    )

@generation_router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext) -> None:
    """Обработка успешного платежа"""
    payment = message.successful_payment
    payload = payment.invoice_payload
    payment_charge_id = payment.telegram_payment_charge_id
    
    # Проверяем тип платежа
    if payload.startswith("package:"):
        # Это покупка пакета
        parts = payload.split(":")
        session_id = parts[1]
        package_size = int(parts[2])
        
        # Пополняем баланс
        new_balance = await balance_service.process_package_purchase(
            message.from_user.id,
            package_size,
            payment_charge_id
        )
        
        # Сохраняем информацию о платеже
        await payment_service.save_payment(
            session_id=session_id,
            user_id=message.from_user.id,
            payment_charge_id=payment_charge_id,
            amount=payment.total_amount
        )
        
        await message.answer(
            f"✅ Оплата получена!\n\n"
            f"💎 Добавлено генераций: {package_size}\n"
            f"📊 Текущий баланс: {new_balance}\n\n"
            f"🎨 Начинаю генерацию..."
        )
        
        # Запускаем отложенную генерацию
        await process_generation(message, state, session_id)
    else:
        # Это обычная оплата за одну генерацию
        session_id = payload
        
        # Сохраняем информацию о платеже
        await payment_service.save_payment(
            session_id=session_id,
            user_id=message.from_user.id,
            payment_charge_id=payment_charge_id,
            amount=GENERATION_PRICE
        )
        
        await message.answer(messages.PAYMENT_RECEIVED)
        await process_generation(message, state, session_id)


async def process_generation(message: Message, state: FSMContext, session_id: str) -> None:
    """Добавить генерацию в очередь"""
    session = await payment_service.get_session(session_id)
    if not session:
        await message.answer(messages.ERROR_SESSION_NOT_FOUND)
        await state.clear()
        return
    
    # Добавляем в очередь
    queue_id = await queue_service.add_to_queue(session_id, message.from_user.id)
    
    # Получаем позицию в очереди
    queue_position = await queue_service.get_queue_position(session_id)
    
    if queue_position and queue_position > 1:
        await message.answer(
            messages.GENERATION_QUEUED.format(position=queue_position)
        )
    else:
        await message.answer(messages.GENERATION_STARTED)
    
    # Сохраняем информацию о сообщении для последующей отправки результата
    await state.update_data(
        queue_id=queue_id,
        chat_id=message.chat.id,
        session_id=session_id
    )
    
    # Очищаем состояние FSM но не удаляем сессию - она будет удалена после генерации
    await state.set_state(None)

@generation_router.message(ImageGenerationStates.waiting_for_prompt)
async def wrong_content_prompt(message: Message) -> None:
    """Обработка неверного типа контента при ожидании промпта"""
    await message.answer(messages.WRONG_CONTENT_PROMPT)


async def show_package_options(message: Message) -> None:
    """Показать варианты пакетов для покупки"""
    await message.answer(
        "💳 <b>У вас закончились генерации</b>\n\n"
        "Выберите пакет для продолжения:\n\n"
        "💡 <i>Чем больше пакет, тем выгоднее цена!</i>",
        reply_markup=get_package_keyboard(),
        parse_mode="HTML"
    )


@generation_router.callback_query(ImageGenerationStates.choosing_package, F.data.startswith("package:"))
async def handle_package_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора пакета"""
    await callback.answer()
    
    # Парсим данные из callback
    parts = callback.data.split(":")
    
    if parts[1] == "cancel":
        await callback.message.edit_text("❌ Генерация отменена")
        await state.clear()
        return
    
    package_size = int(parts[1])
    package_price = int(parts[2])
    
    # Получаем данные из состояния
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await callback.message.edit_text("❌ Ошибка: сессия не найдена")
        await state.clear()
        return
    
    # Обновляем состояние для покупки пакета
    await state.update_data(
        package_size=package_size,
        package_price=package_price
    )
    
    # Создаем инвойс для пакета
    await callback.message.edit_text(f"Создаю инвойс для пакета {package_size} генераций...")
    
    # Переходим в состояние ожидания оплаты
    await state.set_state(ImageGenerationStates.waiting_for_payment)
    
    # Создаем специальный инвойс для пакета
    await payment_service.create_package_invoice(
        callback.message,
        session_id,
        package_size,
        package_price
    )