from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import MAX_IMAGES_PER_REQUEST
from .. import messages

image_router = Router()

# Обработчики для состояния waiting_for_images больше не нужны,
# так как теперь изображения обрабатываются вместе с текстом
# в generation_handlers.py