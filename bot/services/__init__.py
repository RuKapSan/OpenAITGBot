"""
Единая точка инициализации всех сервисов
"""

from ..repositories.sqlite import SQLiteBalanceRepository, SQLiteSessionRepository, SQLitePaymentRepository
from .balance_service import BalanceService
from .payment_service import PaymentService

# Инициализируем репозитории
balance_repository = SQLiteBalanceRepository()
session_repository = SQLiteSessionRepository()
payment_repository = SQLitePaymentRepository()

# Инициализируем сервисы
balance_service = BalanceService(balance_repository)
payment_service = PaymentService(session_repository, payment_repository)

# Экспортируем сервисы для удобного импорта
__all__ = ['balance_service', 'payment_service']