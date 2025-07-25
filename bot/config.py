import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def safe_int(value: str, default: int) -> int:
    """Безопасно преобразует строку в целое число с валидацией"""
    try:
        result = int(value)
        return max(0, result)  # Гарантируем неотрицательное значение
    except (ValueError, TypeError):
        return default

# Настройка основного логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем директорию для логов
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Настройка логгера для платежей
payment_logger = logging.getLogger("payments")
payment_logger.setLevel(logging.INFO)

# Ротация логов платежей (максимум 10MB, хранить 5 файлов)
payment_handler = RotatingFileHandler(
    LOG_DIR / "payments.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
payment_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
)
payment_logger.addHandler(payment_handler)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
ADMIN_ID = safe_int(os.getenv("ADMIN_ID", "0"), 0)  # ID админа для команд управления

GENERATION_PRICE = safe_int(os.getenv("GENERATION_PRICE", "20"), 20)  # Stars
MAX_IMAGES_PER_REQUEST = safe_int(os.getenv("MAX_IMAGES_PER_REQUEST", "3"), 3)  # Максимум изображений для редактирования
MAX_PROMPT_LENGTH = safe_int(os.getenv("MAX_PROMPT_LENGTH", "1000"), 1000)  # Максимальная длина промпта
OPENAI_CONCURRENT_LIMIT = safe_int(os.getenv("OPENAI_CONCURRENT_LIMIT", "5"), 5)  # Лимит одновременных запросов к OpenAI API
SESSION_EXPIRE_MINUTES = safe_int(os.getenv("SESSION_EXPIRE_MINUTES", "60"), 60)  # Время жизни сессии оплаты в минутах

# Конфигурация пакетов генераций
# Каждый пакет определяет количество генераций и цену в Stars
PACKAGES = [
    {
        "size": safe_int(os.getenv("PACKAGE_1_SIZE", "1"), 1),
        "price": safe_int(os.getenv("PACKAGE_1_PRICE", "20"), 20)
    },
    {
        "size": safe_int(os.getenv("PACKAGE_2_SIZE", "5"), 5),
        "price": safe_int(os.getenv("PACKAGE_2_PRICE", "90"), 90)
    },
    {
        "size": safe_int(os.getenv("PACKAGE_3_SIZE", "10"), 10),
        "price": safe_int(os.getenv("PACKAGE_3_PRICE", "160"), 160)
    },
    {
        "size": safe_int(os.getenv("PACKAGE_4_SIZE", "20"), 20),
        "price": safe_int(os.getenv("PACKAGE_4_PRICE", "280"), 280)
    }
]

# URL для изображения в инвойсе
INVOICE_PHOTO_URL = os.getenv(
    "INVOICE_PHOTO_URL", 
    "https://cdn-icons-png.flaticon.com/512/2779/2779775.png"
)

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо установить BOT_TOKEN и OPENAI_API_KEY в .env файле")