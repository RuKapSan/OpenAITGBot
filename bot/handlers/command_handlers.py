from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import logger, ADMIN_ID, GENERATION_PRICE, MAX_IMAGES_PER_REQUEST
from ..services import payment_service, balance_service
from .. import messages

command_router = Router()

@command_router.message(Command("start"))
async def start_command(message: Message) -> None:
    """Обработчик команды /start"""
    await message.answer(
        messages.START_MESSAGE.format(price=GENERATION_PRICE)
    )

@command_router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Подробная инструкция"""
    await message.answer(
        messages.HELP_MESSAGE.format(
            max_images=MAX_IMAGES_PER_REQUEST,
            price=GENERATION_PRICE
        ),
        parse_mode="HTML"
    )

@command_router.message(Command("generate"))
async def generate_command(message: Message, state: FSMContext) -> None:
    """Начать процесс генерации"""
    await state.clear()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    
    from ..keyboards.package_keyboards import get_reset_keyboard
    
    await message.answer(
        messages.GENERATE_START_UNIFIED.format(max_images=MAX_IMAGES_PER_REQUEST),
        parse_mode="HTML",
        reply_markup=get_reset_keyboard()
    )


@command_router.message(Command("balance"))
async def balance_command(message: Message) -> None:
    """Проверить баланс генераций"""
    user_balance = await balance_service.get_balance(message.from_user.id)
    
    if user_balance > 0:
        await message.answer(
            f"💎 <b>Ваш баланс</b>\n\n"
            f"Доступно генераций: {user_balance}\n\n"
            f"Используйте /generate для создания изображения",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"💎 <b>Ваш баланс</b>\n\n"
            f"Доступно генераций: 0\n\n"
            f"Для генерации изображений необходимо пополнить баланс.\n"
            f"Используйте /generate и выберите подходящий пакет.",
            parse_mode="HTML"
        )


@command_router.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    """Поддержка по платежам"""
    await message.answer(
        messages.PAYMENT_SUPPORT_MESSAGE,
        parse_mode="HTML"
    )


@command_router.message(Command("refund"))
async def cmd_refund(message: Message) -> None:
    """Ручной возврат платежа (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer(messages.REFUND_NO_PERMISSION)
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer(messages.REFUND_USAGE)
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
            await message.answer(messages.REFUND_SUCCESS.format(message=msg))
        else:
            await message.answer(messages.REFUND_ERROR.format(message=msg))
            
    except ValueError:
        await message.answer(messages.REFUND_INVALID_USER_ID)
    except (AttributeError, TypeError) as e:
        logger.error(f"Ошибка при ручном возврате: {e}")
        await message.answer(f"❌ Ошибка при обработке команды")


@command_router.message(F.text == "🔄 Начать заново")
async def reset_state(message: Message, state: FSMContext) -> None:
    """Сброс состояния и начало заново"""
    await state.clear()
    await message.answer(
        "✅ Состояние сброшено. Вы можете начать заново.\n\n"
        "Используйте /generate для создания нового изображения.",
        reply_markup=ReplyKeyboardRemove()
    )