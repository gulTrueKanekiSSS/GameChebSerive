import asyncio
import os
import django

# Указываем путь к settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')
django.setup()

from bot.bot import start_bot  # Импорт start_bot функции

if __name__ == "__main__":
    asyncio.run(start_bot())