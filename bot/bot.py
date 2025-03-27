import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from django.conf import settings
from core.models import User, Quest, UserQuestProgress
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

# Импортируем административные команды
from . import admin_commands

# Явно загружаем переменные окружения
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен напрямую из переменных окружения
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"Используемый токен из переменных окружения: {token}")

# Инициализируем бота и диспетчер с новым синтаксисом
bot = Bot(
    token=token,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Регистрируем административные команды
dp.message.register(admin_commands.handle_approve, Command("approve"))
dp.message.register(admin_commands.handle_reject, Command("reject"))

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Получить квест")],
            [KeyboardButton(text="🎁 Мои промокоды")],
        ],
        resize_keyboard=True
    )
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_or_create = sync_to_async(User.objects.get_or_create)
    user, created = await get_or_create(
        telegram_id=message.from_user.id,
        defaults={
            'name': message.from_user.full_name,
        }
    )
    
    if not user.is_verified:
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
            resize_keyboard=True
        )
        await message.answer(
            "Добро пожаловать! Для начала работы, пожалуйста, поделитесь своим номером телефона.",
            reply_markup=contact_keyboard
        )
    else:
        await message.answer(
            "Добро пожаловать в систему квестов! Выберите действие:",
            reply_markup=get_main_keyboard()
        )

@dp.message(lambda message: message.contact is not None)
async def handle_contact(message: types.Message):
    get_user = sync_to_async(User.objects.get)
    user = await get_user(telegram_id=message.from_user.id)
    user.phone_number = message.contact.phone_number
    user.is_verified = True
    save_user = sync_to_async(user.save)
    await save_user()
    
    await message.answer(
        "Спасибо! Теперь вы можете начать выполнять квесты.",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "🎯 Получить квест")
async def get_quest(message: types.Message):
    get_user = sync_to_async(User.objects.get)
    user = await get_user(telegram_id=message.from_user.id)
    
    if not user.is_verified:
        await message.answer("Пожалуйста, сначала подтвердите свой номер телефона.")
        return
    
    get_quest = sync_to_async(lambda: Quest.objects.filter(
        is_active=True
    ).exclude(
        userquestprogress__user=user
    ).first())
    available_quest = await get_quest()
    
    if not available_quest:
        await message.answer("К сожалению, сейчас нет доступных квестов.")
        return
    
    # Отправляем описание квеста
    await message.answer(
        f"🎯 Квест: {available_quest.name}\n\n"
        f"📍 Локация: {available_quest.location}\n\n"
        f"📝 Описание:\n{available_quest.description}\n\n"
        "Для подтверждения выполнения квеста отправьте фото."
    )
    
    # Проверяем и отправляем локацию
    logger.info(f"Координаты квеста: lat={available_quest.latitude}, lon={available_quest.longitude}")
    
    try:
        if available_quest.latitude and available_quest.longitude:
            await message.answer_location(
                latitude=float(available_quest.latitude),
                longitude=float(available_quest.longitude)
            )
            logger.info("Локация успешно отправлена")
        else:
            logger.warning("Для квеста не указаны координаты")
    except Exception as e:
        logger.error(f"Ошибка при отправке локации: {e}")
        await message.answer("К сожалению, не удалось отправить карту местоположения.")

@dp.message(lambda message: message.text == "🎁 Мои промокоды")
async def my_promocodes(message: types.Message):
    get_user = sync_to_async(User.objects.get)
    user = await get_user(telegram_id=message.from_user.id)
    
    get_completed_quests = sync_to_async(lambda: list(UserQuestProgress.objects.filter(
        user=user,
        status=UserQuestProgress.Status.APPROVED,
        promo_code__isnull=False
    ).select_related('quest', 'promo_code')))
    
    completed_quests = await get_completed_quests()
    
    if not completed_quests:
        await message.answer("У вас пока нет полученных промокодов.")
        return
    
    promocodes_text = "Ваши промокоды:\n\n"
    for progress in completed_quests:
        promocodes_text += f"🎁 Квест: {progress.quest.name}\n"
        promocodes_text += f"🎫 Промокод: {progress.promo_code.code}\n\n"
    
    await message.answer(promocodes_text)

@dp.message(lambda message: message.photo is not None)
async def handle_photo(message: types.Message):
    get_user = sync_to_async(User.objects.get)
    user = await get_user(telegram_id=message.from_user.id)
    
    get_quest = sync_to_async(lambda: Quest.objects.filter(
        is_active=True
    ).exclude(
        userquestprogress__user=user
    ).first())
    active_quest = await get_quest()
    
    if not active_quest:
        await message.answer("У вас нет активного квеста.")
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    create_progress = sync_to_async(UserQuestProgress.objects.create)
    progress = await create_progress(
        user=user,
        quest=active_quest,
        photo=file_id
    )
    
    await message.answer(
        "Фото получено! Администратор проверит выполнение квеста и вы получите уведомление."
    )
    
    # Отправляем фото в чат администраторов
    await bot.send_photo(
        settings.ADMIN_GROUP_ID,
        photo=file_id,
        caption=(
            f"Новое выполнение квеста!\n\n"
            f"👤 Пользователь: {user.name}\n"
            f"🎯 Квест: {active_quest.name}\n"
            f"🆔 ID прогресса: {progress.id}\n\n"
            "Для подтверждения используйте команду:\n"
            f"/approve {progress.id}\n\n"
            "Для отклонения:\n"
            f"/reject {progress.id} причина"
        )
    )

async def start_bot():
    # Регистрируем хендлеры
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_contact, lambda message: message.contact is not None)
    dp.message.register(get_quest, lambda message: message.text == "🎯 Получить квест")
    dp.message.register(my_promocodes, lambda message: message.text == "🎁 Мои промокоды")
    dp.message.register(handle_photo, lambda message: message.photo is not None)
    
    try:
        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise 