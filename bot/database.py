import asyncio
from pathlib import Path

from .repositories.sqlite import init_database
from .migrations.migration_system import MigrationSystem
from .config import logger


async def setup_database() -> None:
    """Настройка базы данных при запуске"""
    db_path = Path("bot_data.db")
    
    try:
        # Запускаем миграции
        migration_system = MigrationSystem(str(db_path))
        await migration_system.migrate()
        
        # Для обратной совместимости - создаем таблицы если их нет
        # (на случай если БД уже существует без миграций)
        await init_database(str(db_path))
        
        logger.info(f"База данных настроена: {db_path.absolute()}")
    except (IOError, OSError, RuntimeError) as e:
        logger.error(f"Ошибка настройки БД: {e}")
        raise


if __name__ == "__main__":
    # Для ручной инициализации БД
    asyncio.run(setup_database())