from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from ..states import ImageGenerationStates

image_router = Router()

@image_router.callback_query(F.data == "skip_images")
async def skip_images(callback: CallbackQuery, state: FSMContext):
    """Пропустить загрузку изображений"""
    await callback.answer()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    await callback.message.edit_text(
        "✍️ Теперь опишите, какое изображение вы хотите получить.\n\n"
        "Чем подробнее описание, тем лучше результат!"
    )

@image_router.message(ImageGenerationStates.waiting_for_images, F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, state: FSMContext):
    """Обработка загруженных фото"""
    data = await state.get_data()
    images = data.get('images', [])
    
    photo = message.photo[-1]
    images.append(photo.file_id)
    
    await state.update_data(images=images)
    
    if len(images) >= 3:
        await state.set_state(ImageGenerationStates.waiting_for_prompt)
        await message.answer(
            f"✅ Загружено {len(images)} изображений (максимум).\n\n"
            "✍️ Теперь опишите, что вы хотите сделать с этими изображениями:"
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Продолжить с {len(images)} фото ➡️", 
                callback_data="continue_to_prompt"
            )]
        ])
        await message.answer(
            f"📸 Загружено {len(images)}/3 изображений.\n"
            "Можете отправить еще или продолжить:",
            reply_markup=keyboard
        )

@image_router.callback_query(F.data == "continue_to_prompt")
async def continue_to_prompt(callback: CallbackQuery, state: FSMContext):
    """Перейти к вводу промпта"""
    await callback.answer()
    await state.set_state(ImageGenerationStates.waiting_for_prompt)
    await callback.message.edit_text(
        "✍️ Отлично! Теперь опишите, что вы хотите сделать с этими изображениями:"
    )

@image_router.message(ImageGenerationStates.waiting_for_images)
async def wrong_content_images(message: Message):
    """Обработка неверного типа контента при ожидании изображений"""
    await message.answer(
        "❌ Пожалуйста, отправьте изображение или нажмите 'Пропустить'"
    )