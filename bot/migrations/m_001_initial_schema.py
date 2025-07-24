"""
Начальная схема базы данных
"""
from bot.migrations.migration_system import Migration


class InitialSchema(Migration):
    """Создание начальной схемы БД"""
    
    def __init__(self):
        super().__init__(
            version="001",
            description="Создание таблиц sessions и payments"
        )
    
    async def up(self, db):
        """Создать таблицы"""
        # Таблица сессий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                images TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_charge_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                payment_charge_id TEXT UNIQUE NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                refunded_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        
        # Индексы для быстрого поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_charge_id ON payments(payment_charge_id)")
    
    async def down(self, db):
        """Удалить таблицы"""
        await db.execute("DROP INDEX IF EXISTS idx_payments_charge_id")
        await db.execute("DROP INDEX IF EXISTS idx_payments_user_id")
        await db.execute("DROP INDEX IF EXISTS idx_sessions_created_at")
        await db.execute("DROP INDEX IF EXISTS idx_sessions_user_id")
        await db.execute("DROP TABLE IF EXISTS payments")
        await db.execute("DROP TABLE IF EXISTS sessions")