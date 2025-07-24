from datetime import datetime
from aiogram.types import LabeledPrice
from ..config import GENERATION_PRICE

generation_sessions = {}

def create_session(user_id: int, images: list, prompt: str) -> str:
    """Создать новую сессию генерации"""
    session_id = f"{user_id}_{int(datetime.now().timestamp())}"
    generation_sessions[session_id] = {
        'user_id': user_id,
        'images': images,
        'prompt': prompt,
        'status': 'pending'
    }
    return session_id

def get_session(session_id: str) -> dict:
    """Получить сессию по ID"""
    return generation_sessions.get(session_id)

def delete_session(session_id: str):
    """Удалить сессию"""
    generation_sessions.pop(session_id, None)

async def create_invoice(message, session_id: str, prompt: str, images_count: int):
    """Создать инвойс для оплаты генерации"""
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Генерация изображения",
        description=f"Промпт: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n"
                   f"Изображений: {images_count}",
        payload=session_id,
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(label="Генерация", amount=GENERATION_PRICE)
        ],
        photo_url="https://cdn-icons-png.flaticon.com/512/2779/2779775.png",
        photo_width=512,
        photo_height=512
    )