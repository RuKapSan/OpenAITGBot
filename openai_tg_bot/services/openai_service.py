import base64
import os
import asyncio
from typing import List, Optional
from openai import AsyncOpenAI
from ..config import OPENAI_API_KEY, logger, OPENAI_CONCURRENT_LIMIT
from .. import messages


class GenerationError(Exception):
    """Кастомное исключение для ошибок генерации"""
    pass


# Семафор для ограничения одновременных генераций
generation_semaphore = asyncio.Semaphore(OPENAI_CONCURRENT_LIMIT)

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_image(prompt: str, input_images: Optional[List[bytes]] = None) -> bytes:
    """Генерация изображения через OpenAI API"""
    import tempfile
    temp_files = []
    
    # Ограничиваем количество одновременных запросов
    async with generation_semaphore:
        logger.info(f"Начало генерации. Активных запросов: {OPENAI_CONCURRENT_LIMIT - generation_semaphore._value}/{OPENAI_CONCURRENT_LIMIT}")
        
        try:
            if input_images:
                # Редактирование с входными изображениями
                files = []
                for i, img_bytes in enumerate(input_images):
                    # Используем tempfile для безопасного создания временных файлов
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_files.append(temp_file.name)
                    temp_file.write(img_bytes)
                    temp_file.close()
                    files.append(open(temp_file.name, 'rb'))
                
                try:
                    response = await openai_client.images.edit(
                        model="gpt-image-1",
                        image=files[0] if len(files) == 1 else files,
                        prompt=prompt,
                        n=1,
                        size="1024x1024",
                        quality="high",
                        background="auto"
                    )
                finally:
                    for f in files:
                        f.close()
            else:
                # Генерация с нуля
                response = await openai_client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    quality="high",
                    output_format="jpeg"
                )
            
            image_base64 = response.data[0].b64_json
            return base64.b64decode(image_base64)
            
        except Exception as e:
            logger.error(f"Ошибка генерации: {type(e).__name__}: {e}")
            
            # Обрабатываем разные типы ошибок
            error_message = messages.OPENAI_ERROR_GENERIC
            
            if "rate_limit" in str(e).lower():
                error_message = messages.OPENAI_ERROR_RATE_LIMIT
            elif "invalid_api_key" in str(e).lower():
                error_message = messages.OPENAI_ERROR_AUTH
            elif "model_not_found" in str(e).lower():
                error_message = messages.OPENAI_ERROR_MODEL
            elif "timeout" in str(e).lower():
                error_message = messages.OPENAI_ERROR_TIMEOUT
            elif "insufficient_quota" in str(e).lower():
                error_message = messages.OPENAI_ERROR_QUOTA
            
            # Создаем кастомное исключение с понятным сообщением
            raise GenerationError(error_message) from e
        finally:
            # Всегда удаляем временные файлы
            for temp_path in temp_files:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass  # Игнорируем ошибки удаления