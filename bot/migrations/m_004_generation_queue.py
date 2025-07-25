"""
Миграция для добавления таблицы generation_queue
"""
from bot.migrations.migration_system import Migration
from datetime import datetime


class GenerationQueue(Migration):
    """Создание таблицы generation_queue для персистентной очереди генераций"""
    
    def __init__(self):
        super().__init__(
            version="004",
            description="Создание таблицы generation_queue"
        )
    
    async def up(self, db):
        """Создание таблицы generation_queue"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS generation_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Создаем индексы для быстрого поиска
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_status 
            ON generation_queue(status)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_priority_created 
            ON generation_queue(priority DESC, created_at ASC)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_user_id 
            ON generation_queue(user_id)
        """)
    
    async def down(self, db):
        """Удаление таблицы generation_queue"""
        await db.execute("DROP INDEX IF EXISTS idx_queue_status")
        await db.execute("DROP INDEX IF EXISTS idx_queue_priority_created")
        await db.execute("DROP INDEX IF EXISTS idx_queue_user_id")
        await db.execute("DROP TABLE IF EXISTS generation_queue")