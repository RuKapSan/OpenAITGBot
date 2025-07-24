# OpenAI Telegram Bot

Telegram бот для генерации изображений с использованием OpenAI API.

## Возможности

- Генерация изображений по текстовому описанию
- Редактирование и комбинирование загруженных фотографий
- Оплата через Telegram Stars
- Автоматический возврат средств при ошибках
- SQLite база данных для хранения сессий и платежей

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/OpenAITGBot.git
cd OpenAITGBot
```

2. Установите зависимости используя uv:
```bash
uv pip install -e .
```

Или с pip:
```bash
pip install -e .
```

3. Создайте файл `.env` в корне проекта:
```env
BOT_TOKEN=ваш_токен_бота
OPENAI_API_KEY=ваш_ключ_openai
TEST_MODE=false
ADMIN_ID=ваш_telegram_id

# Настройки генерации (опционально)
GENERATION_PRICE=20
MAX_IMAGES_PER_REQUEST=3
MAX_PROMPT_LENGTH=1000
OPENAI_CONCURRENT_LIMIT=5

# URL изображения для инвойса (опционально)
INVOICE_PHOTO_URL=https://cdn-icons-png.flaticon.com/512/2779/2779775.png
```

## Настройка

### Получение токенов

1. **Bot Token**: Создайте бота через [@BotFather](https://t.me/BotFather)
2. **OpenAI API Key**: Получите на [platform.openai.com](https://platform.openai.com/api-keys)
3. **Admin ID**: Узнайте свой ID через [@userinfobot](https://t.me/userinfobot)

### Настройка платежей

Для работы платежей через Telegram Stars:
1. Включите платежи в настройках бота через BotFather
2. Выберите провайдера "Telegram Stars"
3. Установите цену в `.env` файле (переменная `GENERATION_PRICE`, по умолчанию 20 Stars)

### Настройка параметров генерации

Все основные параметры можно настроить через переменные окружения в `.env`:

- `GENERATION_PRICE` - цена за генерацию в Telegram Stars (по умолчанию: 20)
- `MAX_IMAGES_PER_REQUEST` - максимальное количество изображений для редактирования (по умолчанию: 3)
- `MAX_PROMPT_LENGTH` - максимальная длина промпта в символах (по умолчанию: 1000)
- `OPENAI_CONCURRENT_LIMIT` - лимит одновременных запросов к OpenAI API (по умолчанию: 5)
- `INVOICE_PHOTO_URL` - URL изображения для отображения в инвойсе (опционально)

### Ограничения OpenAI API

OpenAI API имеет лимит на количество одновременных запросов. Бот автоматически:
- Ограничивает количество параллельных генераций через `OPENAI_CONCURRENT_LIMIT`
- Показывает позицию в очереди пользователям
- Обрабатывает ошибки превышения лимита

Для изменения лимита установите `OPENAI_CONCURRENT_LIMIT` в `.env` файле.

## Запуск

```bash
python main.py
```

## Команды бота

- `/start` - Приветствие и информация о боте
- `/help` - Подробная инструкция
- `/generate` - Начать генерацию изображения
- `/paysupport` - Поддержка по платежам
- `/refund` - Ручной возврат платежа (только для админа)

## Структура проекта

```
OpenAITGBot/
├── main.py                          # Точка входа
├── bot/
│   ├── __init__.py                  # Инициализация бота
│   ├── config.py                    # Конфигурация
│   ├── states.py                    # FSM состояния
│   ├── database.py                  # Настройка БД
│   ├── handlers/                    # Обработчики команд
│   │   ├── command_handlers.py      # Основные команды
│   │   ├── generation_handlers_new.py # Генерация изображений
│   │   ├── image_handlers.py        # Обработка изображений
│   │   └── payment_handlers.py      # Обработка платежей
│   ├── services/                    # Бизнес-логика
│   │   ├── openai_service.py        # Интеграция с OpenAI
│   │   ├── payment_service_new.py   # Сервис платежей
│   │   └── telegram_service.py      # Telegram утилиты
│   └── repositories/                # Слой данных
│       ├── base.py                  # Абстрактные репозитории
│       └── sqlite.py                # SQLite реализация
└── bot_data.db                      # База данных (создается автоматически)
```

## Режим разработки

Для тестирования без оплаты установите в `.env`:
```env
TEST_MODE=true
```

## Безопасность

- Храните токены в `.env` файле
- Не коммитьте `.env` в репозиторий
- Регулярно очищайте старые сессии из БД
- Мониторьте логи на предмет подозрительной активности

## Обновления

### Миграция базы данных

#### Автоматические миграции

При запуске бот автоматически применяет все новые миграции. Никаких дополнительных действий не требуется.

#### Ручное управление миграциями

Для управления миграциями используйте скрипт `manage_migrations.py`:

```bash
# Показать статус миграций
python manage_migrations.py status

# Применить все новые миграции
python manage_migrations.py migrate

# Откатить последнюю миграцию
python manage_migrations.py rollback

# Откатить до конкретной версии
python manage_migrations.py rollback 001
```

#### Создание новой миграции

1. Создайте файл в `bot/migrations/` с именем `m_XXX_description.py`
   где XXX - номер версии (например, 003)

2. Создайте класс миграции:
```python
from .migration_system import Migration

class YourMigration(Migration):
    def __init__(self):
        super().__init__(
            version="003",
            description="Описание изменений"
        )
    
    async def up(self, db):
        # Применить изменения
        await db.execute("ALTER TABLE ...")
    
    async def down(self, db):
        # Откатить изменения
        await db.execute("ALTER TABLE ...")
```

#### Миграция со старой версии без БД

Если вы использовали версию без БД:
1. Остановите бота
2. Обновите код
3. Запустите бота - БД и все миграции применятся автоматически
4. Старые сессии в памяти будут потеряны

### Обновление зависимостей

```bash
uv pip sync
```

## Поддержка

При возникновении проблем:
1. Проверьте логи бота
2. Убедитесь что все токены правильные
3. Проверьте наличие файла `bot_data.db`
4. Создайте issue в репозитории