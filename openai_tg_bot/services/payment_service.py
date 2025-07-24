from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import LabeledPrice, Message

from ..config import GENERATION_PRICE, logger, TEST_MODE
from ..repositories.base import SessionRepository, PaymentRepository
from ..repositories.sqlite import SQLiteSessionRepository, SQLitePaymentRepository


class PaymentService:
    """Сервис для работы с платежами"""
    
    def __init__(
        self, 
        session_repo: Optional[SessionRepository] = None,
        payment_repo: Optional[PaymentRepository] = None
    ):
        self.session_repo = session_repo or SQLiteSessionRepository()
        self.payment_repo = payment_repo or SQLitePaymentRepository()
    
    async def create_session(self, user_id: int, images: list, prompt: str) -> str:
        """Создать новую сессию генерации"""
        # Ограничиваем длину промпта
        if len(prompt) > 1000:
            raise ValueError("Промпт слишком длинный (максимум 1000 символов)")
        
        # Очищаем старые сессии
        await self.session_repo.cleanup_expired_sessions()
        
        return await self.session_repo.create_session(user_id, images, prompt)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Получить сессию по ID"""
        return await self.session_repo.get_session(session_id)
    
    async def delete_session(self, session_id: str):
        """Удалить сессию"""
        await self.session_repo.delete_session(session_id)
    
    async def create_invoice(
        self, 
        message: Message, 
        session_id: str, 
        prompt: str, 
        images_count: int
    ):
        """Создать инвойс для оплаты генерации"""
        await message.bot.send_invoice(
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
    
    async def save_payment(
        self,
        session_id: str,
        user_id: int,
        payment_charge_id: str,
        amount: int = GENERATION_PRICE
    ) -> int:
        """Сохранить информацию о платеже"""
        # Обновляем сессию
        await self.session_repo.update_session(
            session_id, 
            status='paid',
            payment_charge_id=payment_charge_id
        )
        
        # Сохраняем платеж
        return await self.payment_repo.save_payment(
            session_id=session_id,
            user_id=user_id,
            payment_charge_id=payment_charge_id,
            amount=amount,
            status='completed'
        )
    
    async def refund_payment(
        self,
        bot: Bot,
        user_id: int,
        payment_charge_id: str
    ) -> Tuple[bool, str]:
        """Возврат платежа Stars"""
        try:
            # Проверяем, не был ли уже возвращен
            payment = await self.payment_repo.get_payment_by_charge_id(payment_charge_id)
            if payment and payment['status'] == 'refunded':
                return False, "Платеж уже был возвращен"
            
            # Выполняем возврат
            await bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=payment_charge_id
            )
            
            # Обновляем статус в БД
            if payment:
                await self.payment_repo.update_payment_status(
                    payment['id'], 
                    'refunded'
                )
            
            logger.info(f"Возврат платежа {payment_charge_id} для пользователя {user_id}")
            return True, "Платеж успешно возвращен"
            
        except Exception as e:
            logger.error(f"Ошибка возврата платежа {payment_charge_id}: {e}")
            return False, f"Ошибка возврата: {str(e)}"
    
    async def process_payment_error(
        self,
        bot: Bot,
        message: Message,
        session_id: str,
        error: Exception
    ):
        """Обработать ошибку после платежа с автоматическим возвратом"""
        session = await self.get_session(session_id)
        if not session or not session.get('payment_charge_id'):
            await message.answer(
                "❌ Ошибка генерации.\n"
                "⚠️ Не удалось выполнить автоматический возврат.\n"
                "Обратитесь в поддержку: /paysupport"
            )
            return
        
        # Пытаемся сделать возврат
        success, msg = await self.refund_payment(
            bot,
            session['user_id'],
            session['payment_charge_id']
        )
        
        if success:
            await message.answer(
                "❌ Ошибка генерации.\n"
                "✅ Платеж автоматически возвращен на ваш баланс Stars!"
            )
        else:
            await message.answer(
                "❌ Ошибка генерации.\n"
                f"⚠️ Сохраните ID для возврата: `{session['payment_charge_id']}`\n"
                "Обратитесь в поддержку: /paysupport",
                parse_mode="Markdown"
            )


# Глобальный экземпляр сервиса
payment_service = PaymentService()