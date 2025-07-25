import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import BOT_TOKEN, logger
from .handlers import command_router, image_router, generation_router, payment_router
from .database import setup_database
from .middleware.rate_limit import RateLimitMiddleware, GenerationRateLimitMiddleware
from .services import queue_service

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main() -> None:
    """Главная функция"""
    # Инициализируем базу данных
    await setup_database()
    
    # Инициализируем сервис очереди
    queue_service.set_bot(bot)
    
    # Восстанавливаем очередь после перезапуска
    await queue_service.restore_queue()
    
    # Добавляем middleware
    dp.message.middleware(RateLimitMiddleware(rate_limit=30, window_seconds=60))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limit=30, window_seconds=60))
    
    # Специальный rate limit для генерации
    generation_router.message.middleware(GenerationRateLimitMiddleware())
    
    # Регистрируем роутеры
    dp.include_router(command_router)
    dp.include_router(image_router)
    dp.include_router(generation_router)
    dp.include_router(payment_router)
    
    # Обработчик остановки
    async def on_shutdown():
        logger.info("Остановка бота...")
        await queue_service.pause_queue()
        await queue_service.cancel_all_tasks()
        logger.info("Очередь остановлена")
    
    # Запускаем бота
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())