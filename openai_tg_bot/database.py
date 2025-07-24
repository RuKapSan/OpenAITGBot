import asyncio
from pathlib import Path

from .repositories.sqlite import init_database
from .config import logger


async def setup_database():
    """Настройка базы данных при запуске"""
    db_path = Path("bot_data.db")
    
    try:
        await init_database(str(db_path))
        logger.info(f"База данных настроена: {db_path.absolute()}")
    except Exception as e:
        logger.error(f"Ошибка настройки БД: {e}")
        raise


if __name__ == "__main__":
    # Для ручной инициализации БД
    asyncio.run(setup_database())