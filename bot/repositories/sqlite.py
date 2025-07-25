import aiosqlite
import secrets
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

from .base import SessionRepository, PaymentRepository, BalanceRepository
from ..config import logger


class SQLiteSessionRepository(SessionRepository):
    """SQLite реализация репозитория сессий"""
    
    def __init__(self, db_path: str = "bot_data.db") -> None:
        self.db_path = db_path
    
    async def create_session(self, user_id: int, images: List[str], prompt: str) -> str:
        """Создать новую сессию"""
        session_id = secrets.token_urlsafe(32)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO sessions (id, user_id, images, prompt, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                json.dumps(images),
                prompt,
                'pending',
                datetime.now().isoformat()
            ))
            await db.commit()
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получить сессию по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'images': json.loads(row['images']),
                        'prompt': row['prompt'],
                        'status': row['status'],
                        'payment_charge_id': row['payment_charge_id'],
                        'created_at': row['created_at']
                    }
        return None
    
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Обновить данные сессии"""
        allowed_fields = {'status': 'status', 'payment_charge_id': 'payment_charge_id'}
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                # Используем только предопределенные имена полей из allowed_fields
                safe_field = allowed_fields[field]
                updates.append(f"{safe_field} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(session_id)
        query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def delete_session(self, session_id: str) -> bool:
        """Удалить сессию"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return True
    
    async def cleanup_expired_sessions(self, expire_minutes: int = 30) -> int:
        """Очистить устаревшие сессии"""
        expire_time = (datetime.now() - timedelta(minutes=expire_minutes)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM sessions 
                WHERE created_at < ? AND status = 'pending'
            """, (expire_time,))
            await db.commit()
            return cursor.rowcount


class SQLitePaymentRepository(PaymentRepository):
    """SQLite реализация репозитория платежей"""
    
    def __init__(self, db_path: str = "bot_data.db") -> None:
        self.db_path = db_path
    
    async def save_payment(
        self, 
        session_id: str,
        user_id: int,
        payment_charge_id: str,
        amount: int,
        status: str = "completed"
    ) -> int:
        """Сохранить информацию о платеже"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO payments (session_id, user_id, payment_charge_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                payment_charge_id,
                amount,
                status,
                datetime.now().isoformat()
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получить платеж по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def get_payment_by_charge_id(self, payment_charge_id: str) -> Optional[Dict[str, Any]]:
        """Получить платеж по charge ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE payment_charge_id = ?", (payment_charge_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def update_payment_status(self, payment_id: int, status: str) -> bool:
        """Обновить статус платежа"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE payments SET status = ? WHERE id = ?",
                (status, payment_id)
            )
            await db.commit()
            return True
    
    async def get_user_payments(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить платежи пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM payments 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


class SQLiteBalanceRepository(BalanceRepository):
    """SQLite реализация репозитория балансов"""
    
    def __init__(self, db_path: str = "bot_data.db") -> None:
        self.db_path = db_path
    
    async def get_balance(self, user_id: int) -> int:
        """Получить баланс пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT balance FROM user_balances WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row['balance']
        return 0
    
    async def add_balance(self, user_id: int, amount: int) -> int:
        """Добавить к балансу пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Сначала пытаемся обновить существующий баланс
            cursor = await db.execute("""
                UPDATE user_balances 
                SET balance = balance + ?, updated_at = ?
                WHERE user_id = ?
            """, (amount, datetime.now().isoformat(), user_id))
            
            if cursor.rowcount == 0:
                # Если записи нет, создаем новую
                await db.execute("""
                    INSERT INTO user_balances (user_id, balance, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, amount, datetime.now().isoformat(), datetime.now().isoformat()))
            
            await db.commit()
            
            # Возвращаем новый баланс
            async with db.execute(
                "SELECT balance FROM user_balances WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else amount
    
    async def deduct_balance(self, user_id: int, amount: int) -> bool:
        """Списать с баланса пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем текущий баланс
            async with db.execute(
                "SELECT balance FROM user_balances WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] < amount:
                    return False
            
            # Списываем баланс
            await db.execute("""
                UPDATE user_balances 
                SET balance = balance - ?, updated_at = ?
                WHERE user_id = ? AND balance >= ?
            """, (amount, datetime.now().isoformat(), user_id, amount))
            
            await db.commit()
            return True
    
    async def create_or_get_balance(self, user_id: int) -> int:
        """Создать баланс если не существует или вернуть существующий"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем существующий баланс
            async with db.execute(
                "SELECT balance FROM user_balances WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
            
            # Создаем новый баланс
            await db.execute("""
                INSERT INTO user_balances (user_id, balance, created_at, updated_at)
                VALUES (?, 0, ?, ?)
            """, (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
            await db.commit()
            
            return 0


async def init_database(db_path: str = "bot_data.db"):
    """Инициализировать базу данных"""
    async with aiosqlite.connect(db_path) as db:
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
        
        # Таблица балансов пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Индексы для быстрого поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_charge_id ON payments(payment_charge_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_balances_user_id ON user_balances(user_id)")
        
        await db.commit()
        
    logger.info("База данных инициализирована")