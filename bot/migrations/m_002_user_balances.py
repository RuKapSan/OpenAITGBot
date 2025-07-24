"""
Миграция для добавления таблицы user_balances
"""

from typing import Any


def up(db: Any):
    """Создание таблицы user_balances"""
    cursor = db.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_balances (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Создаем индекс для быстрого поиска по user_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_balances_user_id 
        ON user_balances(user_id)
    """)
    
    db.commit()


def down(db: Any):
    """Удаление таблицы user_balances"""
    cursor = db.cursor()
    
    cursor.execute("DROP INDEX IF EXISTS idx_user_balances_user_id")
    cursor.execute("DROP TABLE IF EXISTS user_balances")
    
    db.commit()