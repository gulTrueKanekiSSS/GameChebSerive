import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from django.conf import settings
from core.models import User, Quest, UserQuestProgress
from core.models import Route, RouteQuest
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Импортируем административные команды
from . import admin_commands

class RouteBuilderStates(StatesGroup):
    waiting_for_name        = State()  # жду название маршрута
    waiting_for_description = State()  # жду описание маршрута
    waiting_for_add_point   = State()  # выбрать: добавить точку или завершить
    waiting_for_quest_choice    = State()  # жду выбор существ. квеста или /new
    waiting_for_new_quest_name  = State()  # при /new — жду название нового квеста
    waiting_for_new_quest_desc  = State()  # жду описание нового квеста
    waiting_for_new_quest_loc   = State()  # жду локацию нового квеста
    waiting_for_hint_text       = State()  # жду подсказку к точке
    waiting_for_photo           = State()  # жду фото или /skip
    waiting_for_audio           = State()  # жду аудио или /skip
    confirm_point               = State()  # жду потверждения добавления точки
    finish_or_add_next          = State()  # после добавления — жду «Готово» или «Добавить»


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
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрируем административные команды
dp.message.register(admin_commands.handle_approve, Command("approve"))
dp.message.register(admin_commands.handle_reject, Command("reject"))

@sync_to_async
def _sync_save_route(data):
    """
    Синхронная часть сохранения: создаёт Route и связанные RouteQuest.
    """
    # 1) создаём маршрут
    route = Route.objects.create(
        name=data['route_name'],
        description=data['route_description']
    )
    # 2) для каждой точки создаём RouteQuest
    for idx, pt in enumerate(data['points'], start=1):
        RouteQuest.objects.create(
            route=route,
            quest_id=pt['quest_id'],
            order=idx,
            hint_text=pt.get('hint_text', ''),
            photo=pt.get('photo_file'),
            audio=pt.get('audio_file'),
            latitude=pt.get('latitude'),
            longitude=pt.get('longitude'),
        )

async def save_route_to_db(data):
    """
    Асинхронная обёртка для FSM: принимает data из state и сохраняет маршрут.
    """
    await _sync_save_route(data)

def get_main_keyboard(user):
    buttons = [
        [KeyboardButton(text="🎯 Получить квест")],
        [KeyboardButton(text="🎁 Мои промокоды")],
    ]
    if user.is_route_builder:
        buttons.append([KeyboardButton(text="🛠️ Создать маршрут")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=message.from_user.id,
        defaults={'name': message.from_user.full_name},
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
            reply_markup=get_main_keyboard(user)
        )


@dp.message(lambda message: message.text == "🛠️ Создать маршрут")
async def cmd_start_route_builder(message: types.Message, state: FSMContext):
    # 1) Получаем или создаём пользователя
    user, _ = await sync_to_async(User.objects.get_or_create)(
        telegram_id=message.from_user.id,
        defaults={'name': message.from_user.full_name},
    )
    # 2) Проверяем, что он билдeр
    if not user.is_route_builder:
        return await message.reply("❌ У вас нет прав создавать маршруты.")

    # 3) Стартуем FSM: просим название
    await message.answer("🛠️ Введите название нового маршрута:")
    await state.set_state(RouteBuilderStates.waiting_for_name)


@dp.message(RouteBuilderStates.waiting_for_name)
async def process_route_name(message: types.Message, state: FSMContext):
    # Сохраняем название в хранилище FSM
    await state.update_data(route_name=message.text)
    # Спрашиваем описание
    await message.answer("🛠️ Отлично, теперь введите описание маршрута:")
    # Переходим в следующее состояние
    await state.set_state(RouteBuilderStates.waiting_for_description)


@dp.message(RouteBuilderStates.waiting_for_description)
async def process_route_description(message: types.Message, state: FSMContext):
    # Сохраняем описание и инициализируем список точек
    await state.update_data(
        route_description=message.text,
        points=[]
    )
    # Предлагаем добавить первую точку или завершить
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить точку"), KeyboardButton(text="✅ Готово")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Описание принято. Что дальше?",
        reply_markup=kb
    )
    await state.set_state(RouteBuilderStates.waiting_for_add_point)

@dp.message(RouteBuilderStates.waiting_for_add_point)
async def process_add_point(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = message.text

    # Завершение маршрута
    if text == "✅ Готово":
        # Проверяем, есть ли добавленные точки
        if not data.get("points"):
            await message.answer("⚠️ Сначала добавьте хотя бы одну точку маршрута, затем нажмите ✅ Готово.")
            return
        # Сохраняем маршрут в БД
        await save_route_to_db(data)
        await message.answer(
            f"✅ Маршрут «{data['route_name']}» успешно создан! Точек в маршруте: {len(data['points'])}."
        )
        await state.clear()  # очищаем FSM
        return

    # Добавление новой точки
    if text == "➕ Добавить точку":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Выбрать существующий"), KeyboardButton(text="/new")],
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Выберите существующий квест по названию или отправьте команду /new для создания нового квеста:",
            reply_markup=kb
        )
        await state.set_state(RouteBuilderStates.waiting_for_quest_choice)
        return

    # Если пользователь отправил что-то неожиданное
    await message.answer("Пожалуйста, используйте кнопки на экране: ➕ Добавить точку или ✅ Готово.")


@dp.message(RouteBuilderStates.waiting_for_quest_choice)
async def process_quest_choice(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # 1) Если пользователь хочет создать новый квест
    if text.lower() == '/new':
        await message.answer("Введите название нового квеста:")
        return await state.set_state(RouteBuilderStates.waiting_for_new_quest_name)

    # 2) Иначе пытаемся найти существующий квест по полному названию
    quest = await sync_to_async(Quest.objects.filter(name=text).first)()
    if not quest:
        return await message.answer(
            "❌ Квест с таким названием не найден. Пожалуйста, введите корректное название из списка или отправьте /new."
        )

    # 3) Сохраняем выбранный quest в «текущей точке» и переходим к подсказке
    await state.update_data(
        current_point={'quest_id': str(quest.id)}
    )
    await message.answer("Введите текст подсказки для этой точки или отправьте /skip, чтобы пропустить:")
    await state.set_state(RouteBuilderStates.waiting_for_hint_text)


@dp.message(RouteBuilderStates.waiting_for_new_quest_name)
async def process_set_quest_name(message: types.Message, state: FSMContext):
    await state.update_data(quest_name=message.text)
    await message.answer("Введите описание квеста")
    await state.set_state(RouteBuilderStates.waiting_for_new_quest_desc)


@dp.message(RouteBuilderStates.waiting_for_new_quest_desc)
async def process_set_quest_desc(message: types.Message, state: FSMContext):
    await state.update_data(quest_desc=message.text)
    await message.answer("")


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
        reply_markup=get_main_keyboard(user)
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
    dp.message.register(cmd_start_route_builder, lambda msg: msg.text == "🛠️ Создать маршрут")
    dp.message.register(
        process_route_name,
        lambda msg: True,
        RouteBuilderStates.waiting_for_name
    )
    dp.message.register(
        process_route_description,
        lambda msg: True,
        RouteBuilderStates.waiting_for_description
    )
    dp.message.register(
        process_quest_choice,
        lambda msg: True,
        RouteBuilderStates.waiting_for_quest_choice
    )

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