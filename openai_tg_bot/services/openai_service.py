import base64
import os
from typing import List
from openai import AsyncOpenAI
from ..config import OPENAI_API_KEY, logger

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_image(prompt: str, input_images: List[bytes] = None) -> bytes:
    """Генерация изображения через OpenAI API"""
    try:
        if input_images:
            # Редактирование с входными изображениями
            files = []
            for i, img_bytes in enumerate(input_images):
                temp_path = f"temp_image_{i}.png"
                with open(temp_path, 'wb') as f:
                    f.write(img_bytes)
                files.append(open(temp_path, 'rb'))
            
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
                for i, f in enumerate(files):
                    f.close()
                    os.remove(f"temp_image_{i}.png")
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
        logger.error(f"Ошибка генерации: {e}")
        raise