# Quest Telegram Bot

Telegram-бот для организации и выполнения квестов с системой промокодов.

## Функциональность

- Регистрация пользователей через Telegram
- Система квестов с подтверждением выполнения через фото
- Административный интерфейс для проверки выполнения квестов
- Система промокодов

## Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd quest-telegram-bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env и заполните необходимые переменные окружения:
```
TELEGRAM_BOT_TOKEN=your_bot_token
DJANGO_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SENTRY_DSN=your_sentry_dsn
```

5. Примените миграции:
```bash
python manage.py migrate
```

6. Запустите сервер разработки:
```bash
python manage.py runserver
```

7. В отдельном терминале запустите бота:
```bash
python manage.py run_bot
```

## Разработка

- Используйте `black` для форматирования кода
- Используйте `flake8` для проверки стиля кода
- Запускайте тесты с помощью `pytest`

## Структура проекта

```
quest_bot/
├── bot/                    # Код Telegram бота
├── core/                   # Основные модели и утилиты
├── api/                    # REST API
├── admin/                  # Административный интерфейс
└── tests/                  # Тесты
``` 