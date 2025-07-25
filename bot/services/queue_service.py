import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile
from ..config import logger, TEST_MODE
from ..repositories.sqlite import SQLiteQueueRepository, SQLiteSessionRepository
from .openai_service import generate_image, GenerationError, generation_semaphore
from .telegram_service import download_image
from . import payment_service
from .. import messages


queue_repository = SQLiteQueueRepository()
session_repository = SQLiteSessionRepository()

# Флаг для управления паузой
queue_paused = False
# Список активных задач
active_tasks: Dict[int, asyncio.Task] = {}
# Ссылка на бота
bot_instance: Optional[Bot] = None
# Семафор для ограничения параллельных process_queue
queue_processing_semaphore = asyncio.Semaphore(1)
# Задача worker'а очереди
_queue_worker_task: Optional[asyncio.Task] = None


def set_bot(bot: Bot) -> None:
    """Установить экземпляр бота для отправки сообщений"""
    global bot_instance
    bot_instance = bot


async def add_to_queue(session_id: str, user_id: int, priority: int = 0) -> int:
    """Добавить генерацию в очередь"""
    queue_id = await queue_repository.add_to_queue(session_id, user_id, priority)
    logger.info(f"Добавлена задача в очередь: queue_id={queue_id}, session_id={session_id}")
    
    # Убеждаемся что worker запущен
    if not queue_paused:
        await start_queue_worker()
    
    return queue_id


async def pause_queue() -> None:
    """Поставить очередь на паузу"""
    global queue_paused
    queue_paused = True
    logger.info("Очередь поставлена на паузу")


async def resume_queue() -> None:
    """Возобновить обработку очереди"""
    global queue_paused
    queue_paused = False
    logger.info("Очередь возобновлена")
    
    # Запускаем worker
    await start_queue_worker()


async def get_queue_position(session_id: str) -> Optional[int]:
    """Получить позицию в очереди"""
    return await queue_repository.get_queue_position(session_id)


async def queue_items():
    """Асинхронный генератор элементов очереди"""
    while True:
        if queue_paused:
            await asyncio.sleep(1)
            continue
            
        async with queue_processing_semaphore:
            # Получаем следующую задачу (уже помеченную как processing)
            item = await queue_repository.get_next_in_queue()
            if item:
                yield item
            else:
                # Очередь пуста
                await asyncio.sleep(1)


async def queue_worker():
    """Worker для обработки очереди через асинхронный итератор"""
    try:
        async for item in queue_items():
            # Проверяем семафор генерации
            if generation_semaphore._value > 0:
                # Запускаем обработку
                task = asyncio.create_task(process_queue_item(item))
                active_tasks[item['id']] = task
            else:
                # Нет свободных слотов - возвращаем в очередь
                await queue_repository.update_queue_status(item['id'], 'pending')
                logger.info("Нет свободных слотов, элемент возвращен в очередь")
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.info("Queue worker cancelled")
        raise
    except Exception as e:
        logger.error(f"Queue worker error: {e}")
        # Перезапускаем worker через некоторое время
        await asyncio.sleep(5)
        await start_queue_worker()


async def start_queue_worker() -> None:
    """Запустить worker очереди если он еще не запущен"""
    global _queue_worker_task
    
    if _queue_worker_task and not _queue_worker_task.done():
        return  # Worker уже работает
    
    _queue_worker_task = asyncio.create_task(queue_worker())
    logger.info("Queue worker started")


async def process_queue_item(queue_item: Dict[str, Any]) -> None:
    """Обработать элемент очереди"""
    queue_id = queue_item['id']
    session_id = queue_item['session_id']
    user_id = queue_item['user_id']
    
    try:
        # Получаем данные сессии
        session = await session_repository.get_session(session_id)
        if not session:
            raise GenerationError("Сессия не найдена")
        
        # Используем семафор для ограничения
        async with generation_semaphore:
            logger.info(f"Начало генерации для queue_id={queue_id}")
            
            # Проверяем что бот установлен
            if not bot_instance:
                raise GenerationError("Бот не инициализирован")
            
            # Скачиваем изображения если есть
            input_images = []
            if session['images']:
                for file_id in session['images']:
                    img_bytes = await download_image(bot_instance, file_id)
                    input_images.append(img_bytes)
            
            # Генерируем изображение
            result_image = await generate_image(session['prompt'], input_images)
            
            # Обновляем статус на "completed"
            await queue_repository.update_queue_status(queue_id, 'completed')
            logger.info(f"Генерация завершена для queue_id={queue_id}")
            
            # Отправляем результат пользователю
            footer = (
                messages.GENERATION_SUCCESS_FOOTER_TEST 
                if TEST_MODE 
                else messages.GENERATION_SUCCESS_FOOTER_PAID
            )
            
            await bot_instance.send_photo(
                chat_id=user_id,
                photo=BufferedInputFile(result_image, filename="generated.png"),
                caption=messages.GENERATION_SUCCESS.format(
                    prompt=session['prompt'],
                    footer=footer
                ),
                parse_mode="HTML"
            )
            
            # Очищаем сессию
            await payment_service.delete_session(session_id)
            
    except GenerationError as e:
        logger.error(f"Ошибка генерации для queue_id={queue_id}: {e}")
        await queue_repository.update_queue_status(queue_id, 'failed', str(e))
        
        # Отправляем ошибку пользователю
        if bot_instance:
            await bot_instance.send_message(
                chat_id=user_id,
                text=f"❌ {str(e)}"
            )
            
            # Обрабатываем возврат платежа если нужно
            if not TEST_MODE and session and session.get('payment_charge_id'):
                # Создаем фейковый Message объект для совместимости
                class FakeMessage:
                    def __init__(self, bot, chat_id):
                        self.bot = bot
                        self.chat = type('obj', (object,), {'id': chat_id})
                        self.from_user = type('obj', (object,), {'id': user_id})
                
                fake_msg = FakeMessage(bot_instance, user_id)
                await payment_service.process_payment_error(
                    bot_instance,
                    fake_msg,
                    session_id,
                    e
                )
                
    except Exception as e:
        logger.error(f"Неожиданная ошибка для queue_id={queue_id}: {e}")
        await queue_repository.update_queue_status(queue_id, 'failed', str(e))
        
        # Отправляем ошибку пользователю
        if bot_instance:
            await bot_instance.send_message(
                chat_id=user_id,
                text=messages.ERROR_GENERATION_GENERIC
            )
            
            # Обрабатываем возврат платежа если нужно
            if not TEST_MODE and session and session.get('payment_charge_id'):
                class FakeMessage:
                    def __init__(self, bot, chat_id):
                        self.bot = bot
                        self.chat = type('obj', (object,), {'id': chat_id})
                        self.from_user = type('obj', (object,), {'id': user_id})
                
                fake_msg = FakeMessage(bot_instance, user_id)
                await payment_service.process_payment_error(
                    bot_instance,
                    fake_msg,
                    session_id,
                    e
                )
                
    finally:
        # Удаляем из активных задач
        active_tasks.pop(queue_id, None)
        
        # Worker сам продолжит обработку следующего элемента


async def restore_queue() -> None:
    """Восстановить обработку очереди при старте бота"""
    # Очищаем зависшие задачи
    stale_count = await queue_repository.cleanup_stale_items()
    if stale_count > 0:
        logger.info(f"Очищено зависших задач: {stale_count}")
    
    # Получаем количество задач в очереди
    pending_count = await queue_repository.get_pending_count()
    if pending_count > 0:
        logger.info(f"В очереди {pending_count} задач, запускаем обработку")
        
        # Запускаем worker
        await start_queue_worker()


async def cancel_all_tasks() -> None:
    """Отменить все активные задачи (для graceful shutdown)"""
    # Останавливаем worker
    if _queue_worker_task and not _queue_worker_task.done():
        _queue_worker_task.cancel()
        try:
            await _queue_worker_task
        except asyncio.CancelledError:
            pass
    
    # Отменяем активные задачи обработки
    for task in active_tasks.values():
        task.cancel()
    
    # Ждем завершения
    if active_tasks:
        await asyncio.gather(*active_tasks.values(), return_exceptions=True)
    
    active_tasks.clear()
    logger.info("Все активные задачи отменены")