from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import logger, ADMIN_ID
from ..services.payment_service import payment_service

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


@command_router.message(Command("paysupport"))
async def cmd_paysupport(message: Message):
    """Поддержка по платежам"""
    await message.answer(
        "💬 <b>Поддержка по платежам</b>\n\n"
        "Если у вас возникли проблемы с генерацией после оплаты:\n"
        "1. Сохраните ID платежа из сообщения об оплате\n"
        "2. Напишите в поддержку: @your_support_bot\n"
        "3. Укажите ID платежа и опишите проблему\n\n"
        "Возврат осуществляется в течение 24 часов.\n"
        "Stars вернутся на ваш баланс в Telegram.",
        parse_mode="HTML"
    )


@command_router.message(Command("refund"))
async def cmd_refund(message: Message):
    """Ручной возврат платежа (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "Использование: /refund <user_id> <payment_charge_id>\n"
            "Пример: /refund 123456789 payment_12345"
        )
        return
    
    try:
        user_id = int(args[1])
        payment_charge_id = args[2]
        
        success, msg = await payment_service.refund_payment(
            message.bot,
            user_id, 
            payment_charge_id
        )
        
        if success:
            await message.answer(f"✅ {msg}")
        else:
            await message.answer(f"❌ {msg}")
            
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        logger.error(f"Ошибка при ручном возврате: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")