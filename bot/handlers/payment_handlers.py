from aiogram import Router
from aiogram.types import PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup

from ..services import payment_service
from ..config import logger

payment_router = Router()

@payment_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """Подтверждение готовности принять платеж"""
    payload = pre_checkout_query.invoice_payload
    
    # Проверяем тип платежа
    if payload.startswith("package:"):
        # Это покупка пакета
        parts = payload.split(":")
        session_id = parts[1] if len(parts) > 1 else payload
    else:
        # Обычная генерация
        session_id = payload
    
    session = await payment_service.get_session(session_id)
    if not session:
        await pre_checkout_query.bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=False,
            error_message="Сессия истекла. Пожалуйста, начните заново."
        )
        
        # Отправляем сообщение с кнопкой для повторной попытки
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data="retry_payment"
                )]
            ])
            
            await pre_checkout_query.bot.send_message(
                chat_id=pre_checkout_query.from_user.id,
                text="⏰ Сессия оплаты истекла.\n\nНажмите кнопку ниже, чтобы создать новую сессию и повторить попытку.",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о повторе: {e}")
        
        return
    
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )