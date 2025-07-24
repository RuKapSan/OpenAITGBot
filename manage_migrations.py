#!/usr/bin/env python3
"""
Скрипт для управления миграциями БД

Использование:
    python manage_migrations.py status       - показать статус миграций
    python manage_migrations.py migrate      - применить все миграции
    python manage_migrations.py rollback     - откатить последнюю миграцию
    python manage_migrations.py rollback 001 - откатить до версии 001
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from openai_tg_bot.migrations.migration_system import MigrationSystem
from openai_tg_bot.config import logger


async def show_status(db_path: str):
    """Показать статус миграций"""
    system = MigrationSystem(db_path)
    
    # Инициализируем таблицу миграций
    await system.init_migrations_table()
    
    # Получаем информацию
    applied = await system.get_applied_migrations()
    pending = await system.get_pending_migrations()
    
    print("\n=== Статус миграций ===\n")
    
    print("Применённые миграции:")
    if applied:
        for version in applied:
            print(f"  ✓ {version}")
    else:
        print("  (нет)")
    
    print("\nОжидающие миграции:")
    if pending:
        for version, migration in pending:
            print(f"  - {version}: {migration.description}")
    else:
        print("  (нет)")
    
    print()


async def migrate(db_path: str):
    """Применить все миграции"""
    system = MigrationSystem(db_path)
    await system.migrate()


async def rollback(db_path: str, target_version: str = None):
    """Откатить миграции"""
    system = MigrationSystem(db_path)
    
    if target_version:
        print(f"Откат до версии {target_version}...")
    else:
        print("Откат последней миграции...")
    
    await system.rollback(target_version)


async def main():
    """Главная функция"""
    db_path = "bot_data.db"
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        await show_status(db_path)
    
    elif command == "migrate":
        await migrate(db_path)
    
    elif command == "rollback":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        await rollback(db_path, target)
    
    else:
        print(f"Неизвестная команда: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())