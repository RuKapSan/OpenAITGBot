from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from ..config import logger
from .. import messages


class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self, rate_limit: int = 10, window_seconds: int = 60) -> None:
        """
        rate_limit: максимум запросов за период
        window_seconds: период в секундах
        """
        self.rate_limit = rate_limit
        self.window = timedelta(seconds=window_seconds)
        self.user_requests: Dict[int, list[datetime]] = {}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка rate limit перед обработкой события"""
        user_id = event.from_user.id
        now = datetime.now()
        
        # Получаем историю запросов пользователя
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Удаляем старые запросы
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if now - req_time < self.window
        ]
        
        # Проверяем лимит
        if len(self.user_requests[user_id]) >= self.rate_limit:
            # Вычисляем, когда можно будет сделать следующий запрос
            oldest_request = min(self.user_requests[user_id])
            wait_time = (oldest_request + self.window - now).total_seconds()
            
            logger.warning(f"Rate limit для пользователя {user_id}: ждать {int(wait_time)} сек")
            
            # Тихо игнорируем запрос для CallbackQuery
            if isinstance(event, CallbackQuery):
                await event.answer()
            
            return
        
        # Записываем новый запрос
        self.user_requests[user_id].append(now)
        
        # Передаем управление следующему обработчику
        return await handler(event, data)


class GenerationRateLimitMiddleware(RateLimitMiddleware):
    """Специальный rate limit для команды генерации"""
    
    def __init__(self) -> None:
        # 3 генерации в 5 минут
        super().__init__(rate_limit=3, window_seconds=300)