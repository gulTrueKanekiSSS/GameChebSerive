import asyncio
import os
from django.core.management.base import BaseCommand
from bot.bot import start_bot
from django.conf import settings


class Command(BaseCommand):
    help = 'Запускает Telegram бота'

    def handle(self, *args, **options):
        # Проверяем наличие токена
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(
                self.style.ERROR('Ошибка: TELEGRAM_BOT_TOKEN не найден в настройках')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Запускаю Telegram бота с токеном: {settings.TELEGRAM_BOT_TOKEN}')
        )
        
        try:
            asyncio.run(start_bot())
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Ошибка при запуске бота: {str(e)}')
            ) 