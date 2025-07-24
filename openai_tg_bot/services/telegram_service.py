import aiohttp
from ..config import BOT_TOKEN

async def download_image(bot, file_id: str) -> bytes:
    """Скачать изображение из Telegram"""
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as resp:
            return await resp.read()