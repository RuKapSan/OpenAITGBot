from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime


class SessionRepository(ABC):
    """Абстрактный репозиторий для работы с сессиями"""
    
    @abstractmethod
    async def create_session(self, user_id: int, images: List[str], prompt: str) -> str:
        """Создать новую сессию"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получить сессию по ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Обновить данные сессии"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Удалить сессию"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, expire_minutes: int = 30) -> int:
        """Очистить устаревшие сессии"""
        pass


class PaymentRepository(ABC):
    """Абстрактный репозиторий для работы с платежами"""
    
    @abstractmethod
    async def save_payment(
        self, 
        session_id: str,
        user_id: int,
        payment_charge_id: str,
        amount: int,
        status: str = "completed"
    ) -> int:
        """Сохранить информацию о платеже"""
        pass
    
    @abstractmethod
    async def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получить платеж по ID"""
        pass
    
    @abstractmethod
    async def get_payment_by_charge_id(self, payment_charge_id: str) -> Optional[Dict[str, Any]]:
        """Получить платеж по charge ID"""
        pass
    
    @abstractmethod
    async def update_payment_status(self, payment_id: int, status: str) -> bool:
        """Обновить статус платежа"""
        pass
    
    @abstractmethod
    async def get_user_payments(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить платежи пользователя"""
        pass