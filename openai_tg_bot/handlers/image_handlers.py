from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates
from ..config import MAX_IMAGES_PER_REQUEST
from .. import messages

image_router = Router()

@image_router.callback_query(F.data == "skip_images")
async def skip_images(callback: CallbackQuery, state: FSMContext):
    """Пропустить загрузку изображений"""
    await callback.answer()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    await callback.message.edit_text(messages.WAITING_FOR_PROMPT)

@image_router.message(ImageGenerationStates.waiting_for_images, F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, state: FSMContext):
    """Обработка загруженных фото"""
    data = await state.get_data()
    images = data.get('images', [])
    
    photo = message.photo[-1]
    images.append(photo.file_id)
    
    await state.update_data(images=images)
    
    if len(images) >= MAX_IMAGES_PER_REQUEST:
        await state.set_state(ImageGenerationStates.waiting_for_prompt)
        await message.answer(
            messages.IMAGES_MAX_REACHED.format(count=len(images))
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=messages.CONTINUE_BUTTON.format(count=len(images)), 
                callback_data="continue_to_prompt"
            )]
        ])
        await message.answer(
            messages.IMAGES_UPLOADED.format(
                current=len(images),
                max=MAX_IMAGES_PER_REQUEST
            ),
            reply_markup=keyboard
        )

@image_router.callback_query(F.data == "continue_to_prompt")
async def continue_to_prompt(callback: CallbackQuery, state: FSMContext):
    """Перейти к вводу промпта"""
    await callback.answer()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    await callback.message.edit_text(messages.WAITING_FOR_PROMPT_WITH_IMAGES)

@image_router.message(ImageGenerationStates.waiting_for_images)
async def wrong_content_images(message: Message):
    """Обработка неверного типа контента при ожидании изображений"""
    await message.answer(messages.WRONG_CONTENT_IMAGE)