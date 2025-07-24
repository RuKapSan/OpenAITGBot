import aiosqlite
from typing import List, Callable, Tuple
from datetime import datetime
from pathlib import Path
import importlib.util
import inspect

from ..config import logger


class Migration:
    """Базовый класс для миграций"""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
    
    async def up(self, db: aiosqlite.Connection):
        """Применить миграцию"""
        raise NotImplementedError
    
    async def down(self, db: aiosqlite.Connection):
        """Откатить миграцию"""
        raise NotImplementedError


class MigrationSystem:
    """Система управления миграциями БД"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
    
    async def init_migrations_table(self):
        """Создать таблицу для отслеживания миграций"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT,
                    applied_at TEXT NOT NULL
                )
            """)
            await db.commit()
    
    async def get_applied_migrations(self) -> List[str]:
        """Получить список примененных миграций"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT version FROM migrations ORDER BY version") as cursor:
                return [row[0] for row in await cursor.fetchall()]
    
    async def get_pending_migrations(self) -> List[Tuple[str, Migration]]:
        """Получить список непримененных миграций"""
        applied = await self.get_applied_migrations()
        all_migrations = await self.load_migrations()
        
        pending = []
        for version, migration in sorted(all_migrations.items()):
            if version not in applied:
                pending.append((version, migration))
        
        return pending
    
    async def load_migrations(self) -> dict[str, Migration]:
        """Загрузить все миграции из файлов"""
        migrations = {}
        
        # Ищем все файлы миграций
        for file_path in sorted(self.migrations_dir.glob("m_*.py")):
            # Динамически импортируем модуль
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Ищем класс миграции в модуле
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Migration) and 
                    obj is not Migration):
                    migration = obj()
                    migrations[migration.version] = migration
                    break
        
        return migrations
    
    async def apply_migration(self, version: str, migration: Migration):
        """Применить одну миграцию"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Начинаем транзакцию
                await db.execute("BEGIN")
                
                # Применяем миграцию
                await migration.up(db)
                
                # Записываем в таблицу миграций
                await db.execute("""
                    INSERT INTO migrations (version, description, applied_at)
                    VALUES (?, ?, ?)
                """, (version, migration.description, datetime.now().isoformat()))
                
                # Коммитим транзакцию
                await db.commit()
                
                logger.info(f"Миграция {version} применена: {migration.description}")
                
            except Exception as e:
                # Откатываем транзакцию при ошибке
                await db.rollback()
                logger.error(f"Ошибка применения миграции {version}: {e}")
                raise
    
    async def migrate(self):
        """Применить все непримененные миграции"""
        # Инициализируем таблицу миграций
        await self.init_migrations_table()
        
        # Получаем непримененные миграции
        pending = await self.get_pending_migrations()
        
        if not pending:
            logger.info("Все миграции уже применены")
            return
        
        logger.info(f"Найдено {len(pending)} непримененных миграций")
        
        # Применяем миграции по порядку
        for version, migration in pending:
            await self.apply_migration(version, migration)
        
        logger.info("Все миграции успешно применены")
    
    async def rollback(self, target_version: str = None):
        """Откатить миграции до указанной версии"""
        applied = await self.get_applied_migrations()
        all_migrations = await self.load_migrations()
        
        if not applied:
            logger.info("Нет примененных миграций для отката")
            return
        
        # Определяем миграции для отката
        to_rollback = []
        for version in reversed(applied):
            if target_version and version <= target_version:
                break
            if version in all_migrations:
                to_rollback.append((version, all_migrations[version]))
        
        if not to_rollback:
            logger.info("Нет миграций для отката")
            return
        
        # Откатываем миграции
        for version, migration in to_rollback:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute("BEGIN")
                    
                    # Откатываем миграцию
                    await migration.down(db)
                    
                    # Удаляем из таблицы миграций
                    await db.execute("DELETE FROM migrations WHERE version = ?", (version,))
                    
                    await db.commit()
                    logger.info(f"Миграция {version} откачена")
                    
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Ошибка отката миграции {version}: {e}")
                    raise