import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import BOT_TOKEN, logger
from .handlers import command_router, image_router, generation_router, payment_router
from .database import setup_database

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    """Главная функция"""
    # Инициализируем базу данных
    await setup_database()
    
    # Регистрируем роутеры
    dp.include_router(command_router)
    dp.include_router(image_router)
    dp.include_router(generation_router)
    dp.include_router(payment_router)
    
    # Запускаем бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())