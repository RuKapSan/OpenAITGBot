"""
Миграция для оптимизации индексов generation_queue
"""
from bot.migrations.migration_system import Migration


class OptimizeQueueIndices(Migration):
    """Добавление индексов для оптимизации производительности очереди"""
    
    def __init__(self):
        super().__init__(
            version="005",
            description="Оптимизация индексов для generation_queue"
        )
    
    async def up(self, db):
        """Добавление новых индексов"""
        # Индекс на session_id для быстрого поиска позиции
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_session_id 
            ON generation_queue(session_id)
        """)
        
        # Композитный индекс для WHERE status = 'pending' ORDER BY priority, created_at
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_pending_priority_created 
            ON generation_queue(status, priority DESC, created_at ASC)
            WHERE status = 'pending'
        """)
        
        # Индекс для быстрой очистки старых записей
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_completed_at 
            ON generation_queue(completed_at)
            WHERE status IN ('completed', 'failed')
        """)
    
    async def down(self, db):
        """Удаление индексов"""
        await db.execute("DROP INDEX IF EXISTS idx_queue_session_id")
        await db.execute("DROP INDEX IF EXISTS idx_queue_pending_priority_created")
        await db.execute("DROP INDEX IF EXISTS idx_queue_completed_at")