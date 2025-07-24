from aiogram.fsm.state import State, StatesGroup

class ImageGenerationStates(StatesGroup):
    waiting_for_images = State()
    waiting_for_prompt = State()
    waiting_for_payment = State()