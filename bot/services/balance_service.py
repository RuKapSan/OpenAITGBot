"""
Сервис для управления балансами пользователей
"""

from typing import Optional
from ..repositories.base import BalanceRepository
from ..config import logger, payment_logger


class BalanceService:
    """Сервис для работы с балансами пользователей"""
    
    def __init__(self, balance_repository: BalanceRepository):
        self.balance_repo = balance_repository
    
    async def get_balance(self, user_id: int) -> int:
        """Получить текущий баланс пользователя"""
        balance = await self.balance_repo.get_balance(user_id)
        logger.info(f"Проверка баланса пользователя {user_id}: {balance} генераций")
        return balance
    
    async def add_balance(self, user_id: int, amount: int, reason: str = "") -> int:
        """Добавить генерации к балансу пользователя"""
        new_balance = await self.balance_repo.add_balance(user_id, amount)
        
        payment_logger.info(
            f"Пополнение баланса | "
            f"user_id: {user_id} | "
            f"amount: +{amount} | "
            f"new_balance: {new_balance} | "
            f"reason: {reason}"
        )
        
        return new_balance
    
    async def deduct_balance(self, user_id: int, amount: int = 1) -> bool:
        """Списать генерации с баланса пользователя"""
        success = await self.balance_repo.deduct_balance(user_id, amount)
        
        if success:
            new_balance = await self.balance_repo.get_balance(user_id)
            payment_logger.info(
                f"Списание с баланса | "
                f"user_id: {user_id} | "
                f"amount: -{amount} | "
                f"new_balance: {new_balance}"
            )
        else:
            logger.warning(f"Неудачная попытка списания {amount} генераций у пользователя {user_id}")
        
        return success
    
    async def has_balance(self, user_id: int, required_amount: int = 1) -> bool:
        """Проверить, достаточно ли баланса для операции"""
        balance = await self.balance_repo.get_balance(user_id)
        return balance >= required_amount
    
    async def initialize_user(self, user_id: int) -> int:
        """Инициализировать баланс нового пользователя"""
        balance = await self.balance_repo.create_or_get_balance(user_id)
        if balance == 0:
            logger.info(f"Инициализирован баланс для нового пользователя {user_id}")
        return balance
    
    async def process_package_purchase(self, user_id: int, package_size: int, payment_charge_id: str) -> int:
        """Обработать покупку пакета генераций"""
        new_balance = await self.add_balance(
            user_id, 
            package_size, 
            f"Покупка пакета {package_size} генераций (payment_id: {payment_charge_id})"
        )
        
        logger.info(
            f"Обработана покупка пакета | "
            f"user_id: {user_id} | "
            f"package_size: {package_size} | "
            f"payment_id: {payment_charge_id}"
        )
        
        return new_balance