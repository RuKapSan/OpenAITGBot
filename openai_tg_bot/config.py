import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

GENERATION_PRICE = 20  # Stars

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо установить BOT_TOKEN и OPENAI_API_KEY в .env файле")