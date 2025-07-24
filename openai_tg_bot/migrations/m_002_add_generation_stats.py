"""
Добавление статистики генераций
"""
from .migration_system import Migration


class AddGenerationStats(Migration):
    """Добавление полей для статистики генераций"""
    
    def __init__(self):
        super().__init__(
            version="002",
            description="Добавление полей generation_time и error_message в sessions"
        )
    
    async def up(self, db):
        """Добавить новые поля"""
        # Добавляем поле для времени генерации
        await db.execute("""
            ALTER TABLE sessions 
            ADD COLUMN generation_time_ms INTEGER
        """)
        
        # Добавляем поле для сообщения об ошибке
        await db.execute("""
            ALTER TABLE sessions 
            ADD COLUMN error_message TEXT
        """)
        
        # Добавляем поле для модели генерации
        await db.execute("""
            ALTER TABLE sessions 
            ADD COLUMN model_used TEXT DEFAULT 'gpt-image-1'
        """)
        
        # Создаем новую таблицу для статистики
        await db.execute("""
            CREATE TABLE IF NOT EXISTS generation_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                successful_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                total_generation_time_ms INTEGER DEFAULT 0,
                total_refunded INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        """)
        
        # Индекс для быстрого поиска статистики
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_generation_stats_user_date 
            ON generation_stats(user_id, date)
        """)
    
    async def down(self, db):
        """Откатить изменения"""
        # Удаляем индекс
        await db.execute("DROP INDEX IF EXISTS idx_generation_stats_user_date")
        
        # Удаляем таблицу статистики
        await db.execute("DROP TABLE IF EXISTS generation_stats")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Нужно пересоздать таблицу без новых полей
        await db.execute("""
            CREATE TABLE sessions_new (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                images TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_charge_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Копируем данные
        await db.execute("""
            INSERT INTO sessions_new 
            SELECT id, user_id, images, prompt, status, payment_charge_id, created_at
            FROM sessions
        """)
        
        # Заменяем таблицу
        await db.execute("DROP TABLE sessions")
        await db.execute("ALTER TABLE sessions_new RENAME TO sessions")
        
        # Восстанавливаем индексы
        await db.execute("CREATE INDEX idx_sessions_user_id ON sessions(user_id)")
        await db.execute("CREATE INDEX idx_sessions_created_at ON sessions(created_at)")