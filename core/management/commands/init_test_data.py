import random
import string
from django.core.management.base import BaseCommand
from core.models import Quest, PromoCode


def generate_promo_code(length=8):
    """Генерирует случайный промокод"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


class Command(BaseCommand):
    help = 'Инициализирует базу данных тестовыми квестами и промокодами'

    def handle(self, *args, **options):
        # Создаем тестовые квесты
        quests = [
            {
                'name': 'Найти памятник',
                'description': 'Найдите памятник основателю города и сделайте фото на его фоне',
                'location': 'Центральная площадь',
                'latitude': 56.1366,  # Координаты центра Чебоксар
                'longitude': 47.2511
            },
            {
                'name': 'Посетить музей',
                'description': 'Сделайте фото у входа в краеведческий музей',
                'location': 'ул. Ленина, 50',
                'latitude': 56.1325,  # Примерные координаты музея
                'longitude': 47.2482
            },
            {
                'name': 'Городской парк',
                'description': 'Найдите самое старое дерево в парке и сфотографируйтесь рядом с ним',
                'location': 'Городской парк культуры и отдыха',
                'latitude': 56.1391,  # Координаты парка
                'longitude': 47.2488
            },
        ]

        self.stdout.write('Создаю квесты...')
        for quest_data in quests:
            quest = Quest.objects.create(**quest_data)
            self.stdout.write(f'Создан квест: {quest.name}')

            # Создаем промокоды для квеста
            for _ in range(5):  # 5 промокодов для каждого квеста
                promo = PromoCode.objects.create(
                    code=generate_promo_code(),
                    quest=quest
                )
                self.stdout.write(f'Создан промокод: {promo.code} для квеста {quest.name}')

        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно созданы!')) 