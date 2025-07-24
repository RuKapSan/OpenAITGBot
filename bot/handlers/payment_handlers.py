from aiogram import Router
from aiogram.types import PreCheckoutQuery

from ..services.payment_service import payment_service

payment_router = Router()

@payment_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение готовности принять платеж"""
    session_id = pre_checkout_query.invoice_payload
    
    if not await payment_service.get_session(session_id):
        await pre_checkout_query.bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=False,
            error_message="Сессия истекла. Пожалуйста, начните заново."
        )
        return
    
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )