"""
Миграция для добавления таблицы user_balances
"""
from bot.migrations.migration_system import Migration


class UserBalances(Migration):
    """Создание таблицы user_balances"""
    
    def __init__(self):
        super().__init__(
            version="003",
            description="Создание таблицы user_balances"
        )
    
    async def up(self, db):
        """Создание таблицы user_balances"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Создаем индекс для быстрого поиска по user_id
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_balances_user_id 
            ON user_balances(user_id)
        """)
    
    async def down(self, db):
        """Удаление таблицы user_balances"""
        await db.execute("DROP INDEX IF EXISTS idx_user_balances_user_id")
        await db.execute("DROP TABLE IF EXISTS user_balances")