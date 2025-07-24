from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import logger, ADMIN_ID, GENERATION_PRICE, MAX_IMAGES_PER_REQUEST
from ..services.payment_service import payment_service
from .. import messages

command_router = Router()

@command_router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        messages.START_MESSAGE.format(price=GENERATION_PRICE)
    )

@command_router.message(Command("help"))
async def help_command(message: Message):
    """Подробная инструкция"""
    await message.answer(
        messages.HELP_MESSAGE.format(
            max_images=MAX_IMAGES_PER_REQUEST,
            price=GENERATION_PRICE
        ),
        parse_mode="HTML"
    )

@command_router.message(Command("generate"))
async def generate_command(message: Message, state: FSMContext):
    """Начать процесс генерации"""
    await state.clear()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    
    await message.answer(
        messages.GENERATE_START_UNIFIED.format(max_images=MAX_IMAGES_PER_REQUEST),
        parse_mode="HTML"
    )


@command_router.message(Command("paysupport"))
async def cmd_paysupport(message: Message):
    """Поддержка по платежам"""
    await message.answer(
        messages.PAYMENT_SUPPORT_MESSAGE,
        parse_mode="HTML"
    )


@command_router.message(Command("refund"))
async def cmd_refund(message: Message):
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
    except Exception as e:
        logger.error(f"Ошибка при ручном возврате: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")