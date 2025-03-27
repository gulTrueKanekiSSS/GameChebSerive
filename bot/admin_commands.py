from aiogram import types
from aiogram.filters import Command, CommandObject
from asgiref.sync import sync_to_async
from core.models import UserQuestProgress, PromoCode
from django.conf import settings

async def check_admin_group(message: types.Message) -> bool:
    """Проверяет, что сообщение пришло из группы администраторов"""
    if not message.chat.id == int(settings.ADMIN_GROUP_ID):
        await message.reply("Эта команда доступна только в группе администраторов")
        return False
    return True

async def handle_approve(message: types.Message, command: CommandObject):
    # Проверяем, что команда пришла из группы администраторов
    if not await check_admin_group(message):
        return

    if not command.args:
        await message.reply("Ошибка: укажите ID прогресса\nПример: /approve 12345")
        return

    progress_id = command.args

    # Получаем прогресс
    get_progress = sync_to_async(lambda: UserQuestProgress.objects.select_related('user', 'quest').filter(id=progress_id).first())
    progress = await get_progress()

    if not progress:
        await message.reply(f"Ошибка: прогресс с ID {progress_id} не найден")
        return

    if progress.status != UserQuestProgress.Status.PENDING:
        await message.reply("Этот квест уже проверен")
        return

    # Находим свободный промокод
    get_promo = sync_to_async(lambda: PromoCode.objects.filter(
        quest=progress.quest,
        is_used=False
    ).first())
    promo_code = await get_promo()

    if not promo_code:
        await message.reply("Ошибка: нет доступных промокодов для этого квеста")
        return

    # Обновляем статус и привязываем промокод
    @sync_to_async
    def update_progress():
        progress.status = UserQuestProgress.Status.APPROVED
        progress.promo_code = promo_code
        progress.save()
        promo_code.is_used = True
        promo_code.save()

    await update_progress()

    # Отправляем уведомление пользователю
    await message.bot.send_message(
        progress.user.telegram_id,
        f"🎉 Поздравляем! Ваше выполнение квеста \"{progress.quest.name}\" подтверждено!\n\n"
        f"Ваш промокод: {promo_code.code}"
    )

    await message.reply("✅ Квест подтвержден, промокод отправлен пользователю")

async def handle_reject(message: types.Message, command: CommandObject):
    # Проверяем, что команда пришла из группы администраторов
    if not await check_admin_group(message):
        return

    if not command.args:
        await message.reply("Ошибка: укажите ID прогресса и причину\nПример: /reject 12345 фото не соответствует заданию")
        return

    args = command.args.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Ошибка: укажите причину отклонения")
        return

    progress_id, reason = args

    # Получаем прогресс
    get_progress = sync_to_async(lambda: UserQuestProgress.objects.select_related('user', 'quest').filter(id=progress_id).first())
    progress = await get_progress()

    if not progress:
        await message.reply(f"Ошибка: прогресс с ID {progress_id} не найден")
        return

    if progress.status != UserQuestProgress.Status.PENDING:
        await message.reply("Этот квест уже проверен")
        return

    # Обновляем статус и добавляем комментарий
    @sync_to_async
    def update_progress():
        progress.status = UserQuestProgress.Status.REJECTED
        progress.admin_comment = reason
        progress.save()

    await update_progress()

    # Отправляем уведомление пользователю
    await message.bot.send_message(
        progress.user.telegram_id,
        f"❌ К сожалению, ваше выполнение квеста \"{progress.quest.name}\" отклонено.\n\n"
        f"Причина: {reason}\n\n"
        "Вы можете попробовать выполнить квест ещё раз."
    )

    await message.reply("❌ Квест отклонен, уведомление отправлено пользователю") 