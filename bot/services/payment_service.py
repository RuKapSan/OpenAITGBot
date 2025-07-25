from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import LabeledPrice, Message

from ..config import GENERATION_PRICE, logger, payment_logger, TEST_MODE, MAX_PROMPT_LENGTH, INVOICE_PHOTO_URL
from .. import messages
from ..repositories.base import SessionRepository, PaymentRepository
from ..repositories.sqlite import SQLiteSessionRepository, SQLitePaymentRepository
from ..models import SessionCreate, PaymentCreate


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
        # Валидируем данные через Pydantic
        session_data = SessionCreate(user_id=user_id, images=images, prompt=prompt)
        
        # Очищаем старые сессии
        await self.session_repo.cleanup_expired_sessions()
        
        return await self.session_repo.create_session(
            session_data.user_id, 
            session_data.images, 
            session_data.prompt
        )
    
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
        prompt_preview = f"{prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title=messages.INVOICE_TITLE,
            description=messages.INVOICE_DESCRIPTION.format(
                prompt_preview=prompt_preview,
                images_count=images_count
            ),
            payload=session_id,
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(label=messages.INVOICE_LABEL, amount=GENERATION_PRICE)
            ],
            photo_url=INVOICE_PHOTO_URL,
            photo_width=512,
            photo_height=512
        )
    
    async def create_package_invoice(
        self,
        message: Message,
        session_id: str,
        package_size: int,
        package_price: int
    ):
        """Создать инвойс для покупки пакета генераций"""
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title=f"Пакет {package_size} генераций",
            description=f"Покупка {package_size} генераций для создания изображений",
            payload=f"package:{session_id}:{package_size}",
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(label=f"{package_size} генераций", amount=package_price)
            ],
            photo_url=INVOICE_PHOTO_URL,
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
        # Валидируем данные платежа
        payment_data = PaymentCreate(
            session_id=session_id,
            user_id=user_id,
            payment_charge_id=payment_charge_id,
            amount=amount
        )
        
        # Обновляем сессию
        await self.session_repo.update_session(
            payment_data.session_id, 
            status='paid',
            payment_charge_id=payment_data.payment_charge_id
        )
        
        # Сохраняем платеж
        payment_id = await self.payment_repo.save_payment(
            session_id=payment_data.session_id,
            user_id=payment_data.user_id,
            payment_charge_id=payment_data.payment_charge_id,
            amount=payment_data.amount,
            status='completed'
        )
        
        # Логируем платеж
        payment_logger.info(
            f"PAYMENT_COMPLETED | "
            f"user_id={user_id} | "
            f"session_id={session_id} | "
            f"payment_charge_id={payment_charge_id} | "
            f"amount={amount} | "
            f"payment_id={payment_id}"
        )
        
        return payment_id
    
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
                return False, messages.REFUND_ALREADY_DONE
            
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
            
            # Логируем возврат
            payment_logger.info(
                f"PAYMENT_REFUNDED | "
                f"user_id={user_id} | "
                f"payment_charge_id={payment_charge_id} | "
                f"payment_id={payment['id'] if payment else 'unknown'}"
            )
            
            return True, messages.REFUND_SUCCESS_MESSAGE
            
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.error(f"Ошибка возврата платежа {payment_charge_id}: {e}")
            
            # Логируем ошибку возврата
            payment_logger.error(
                f"PAYMENT_REFUND_FAILED | "
                f"user_id={user_id} | "
                f"payment_charge_id={payment_charge_id} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            
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
            await message.answer(messages.ERROR_NO_AUTO_REFUND)
            return
        
        # Пытаемся сделать возврат
        success, msg = await self.refund_payment(
            bot,
            session['user_id'],
            session['payment_charge_id']
        )
        
        if success:
            await message.answer(messages.ERROR_AUTO_REFUND_SUCCESS)
        else:
            await message.answer(
                messages.ERROR_AUTO_REFUND_FAILED.format(
                    payment_charge_id=session['payment_charge_id']
                ),
                parse_mode="Markdown"
            )

