import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ai.claude import generate_digest
from ai.embeddings import get_embedding
from bot.i18n import t
from db import async_session
from db.models import EntryType
from db.queries import (
    get_checkin_users,
    get_digest_users,
    get_entries_for_period,
    get_or_create_user,
    save_entry,
    update_checkin_settings,
    update_digest_settings,
)

logger = logging.getLogger(__name__)

checkin_router = Router()

CHECKIN_QUESTION = "Как прошел день? 🌙"


class CheckinPending(StatesGroup):
    waiting = State()


@checkin_router.message(CheckinPending.waiting)
async def handle_checkin_response(message: Message, state: FSMContext):
    if not message.text:
        return

    text = f"[Чекин] {message.text}"
    embedding = get_embedding(text)
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        lang = user.language or "ru"
        await save_entry(
            session,
            user_id=message.from_user.id,
            type=EntryType.text,
            text=text,
            embedding=embedding,
        )

    await state.clear()
    await message.answer(t(lang, "checkin_saved"))


@checkin_router.message(Command("checkin"))
async def cmd_checkin(message: Message):
    args = message.text.split()[1:]

    if not args:
        await message.answer(
            "Настройка чекина:\n"
            "/checkin on — включить\n"
            "/checkin off — выключить\n"
            "/checkin time 21:00 +5 — время и часовой пояс (UTC offset)"
        )
        return

    cmd = args[0].lower()

    async with async_session() as session:
        user = await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        if cmd == "on":
            await update_checkin_settings(session, message.from_user.id, enabled=True)
            sign = "+" if user.checkin_utc_offset >= 0 else ""
            await message.answer(
                f"Чекин включён. Буду спрашивать в "
                f"{user.checkin_hour:02d}:{user.checkin_minute:02d} "
                f"(UTC{sign}{user.checkin_utc_offset})"
            )

        elif cmd == "off":
            await update_checkin_settings(session, message.from_user.id, enabled=False)
            await message.answer("Чекин выключен.")

        elif cmd == "time" and len(args) >= 3:
            try:
                hour, minute = map(int, args[1].split(":"))
                utc_offset = int(args[2])
                assert 0 <= hour <= 23 and 0 <= minute <= 59 and -12 <= utc_offset <= 14
                await update_checkin_settings(
                    session, message.from_user.id,
                    hour=hour, minute=minute, utc_offset=utc_offset,
                )
                sign = "+" if utc_offset >= 0 else ""
                await message.answer(
                    f"Время чекина: {hour:02d}:{minute:02d} (UTC{sign}{utc_offset})"
                )
            except Exception:
                await message.answer("Неверный формат. Пример: /checkin time 21:00 +5")

        else:
            await message.answer("Неверная команда. Напиши /checkin для справки.")


@checkin_router.message(Command("digest"))
async def cmd_digest(message: Message):
    args = message.text.split()[1:]

    if not args:
        await message.answer(
            "Настройка дайджеста:\n"
            "/digest on — включить\n"
            "/digest off — выключить\n"
            "/digest now — получить прямо сейчас\n"
            "/digest period week — раз в неделю (по умолчанию)\n"
            "/digest period month — раз в месяц\n"
            "/digest format brief — кратко (3-4 пункта)\n"
            "/digest format full — развёрнуто (темы, настроение, события, вывод)\n"
            "/digest format emotional — фокус на эмоциях\n"
            "/digest time 20:00 +5 — время отправки"
        )
        return

    cmd = args[0].lower()

    async with async_session() as session:
        user = await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        if cmd == "on":
            await update_digest_settings(session, message.from_user.id, enabled=True)
            period_label = "неделю" if user.digest_period == "week" else "месяц"
            sign = "+" if user.digest_utc_offset >= 0 else ""
            await message.answer(
                f"Дайджест включён. Раз в {period_label}, "
                f"в {user.digest_hour:02d}:00 (UTC{sign}{user.digest_utc_offset}). "
                f"Формат: {user.digest_format}"
            )

        elif cmd == "off":
            await update_digest_settings(session, message.from_user.id, enabled=False)
            await message.answer("Дайджест выключен.")

        elif cmd == "period" and len(args) >= 2:
            period = args[1].lower()
            if period not in ("week", "month"):
                await message.answer("Доступные варианты: week, month")
                return
            # week: день=6 (воскресенье), month: день=1 (1-е число)
            day = 6 if period == "week" else 1
            await update_digest_settings(session, message.from_user.id, period=period, day=day)
            label = "неделю" if period == "week" else "месяц"
            await message.answer(f"Периодичность: раз в {label}.")

        elif cmd == "format" and len(args) >= 2:
            fmt = args[1].lower()
            if fmt not in ("brief", "full", "emotional"):
                await message.answer("Доступные форматы: brief, full, emotional")
                return
            await update_digest_settings(session, message.from_user.id, format=fmt)
            await message.answer(f"Формат дайджеста: {fmt}.")

        elif cmd == "time" and len(args) >= 3:
            try:
                hour = int(args[1].split(":")[0])
                utc_offset = int(args[2])
                assert 0 <= hour <= 23 and -12 <= utc_offset <= 14
                await update_digest_settings(
                    session, message.from_user.id, hour=hour, utc_offset=utc_offset
                )
                sign = "+" if utc_offset >= 0 else ""
                await message.answer(f"Время дайджеста: {hour:02d}:00 (UTC{sign}{utc_offset})")
            except Exception:
                await message.answer("Неверный формат. Пример: /digest time 20:00 +5")

        elif cmd == "now":
            days = 7 if user.digest_period == "week" else 30
            period_label = "неделю" if user.digest_period == "week" else "месяц"
            async with async_session() as session:
                entries = await get_entries_for_period(session, message.from_user.id, days=days)
            if not entries:
                await message.answer("За этот период записей нет.")
                return
            sent = await message.answer("Генерирую дайджест...")
            text = generate_digest(entries, fmt=user.digest_format, period=period_label)
            await sent.edit_text(f"📋 Дайджест за {period_label}:\n\n{text}")

        else:
            await message.answer("Неверная команда. Напиши /digest для справки.")


async def _check_and_send_digests(bot) -> None:
    now_utc = datetime.now(timezone.utc)

    async with async_session() as session:
        users = await get_digest_users(session)

    for user in users:
        user_local = now_utc + timedelta(hours=user.digest_utc_offset)

        # Проверяем время и день
        if user_local.hour != user.digest_hour:
            continue
        if user.digest_period == "week" and user_local.weekday() != user.digest_day:
            continue
        if user.digest_period == "month" and user_local.day != user.digest_day:
            continue

        try:
            days = 7 if user.digest_period == "week" else 30
            period_label = "неделю" if user.digest_period == "week" else "месяц"
            async with async_session() as session:
                entries = await get_entries_for_period(session, user.id, days=days)
            if not entries:
                continue
            text = generate_digest(entries, fmt=user.digest_format, period=period_label)
            await bot.send_message(user.id, f"📋 Дайджест за {period_label}:\n\n{text}", parse_mode="HTML")
        except Exception as e:
            logger.warning("Digest failed for user %s: %s", user.id, e)


async def _check_and_send_checkins(bot, storage) -> None:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    now_utc = datetime.now(timezone.utc)

    async with async_session() as session:
        users = await get_checkin_users(session)

    for user in users:
        user_local = now_utc + timedelta(hours=user.checkin_utc_offset)
        if user_local.hour == user.checkin_hour and user_local.minute == user.checkin_minute:
            try:
                await bot.send_message(user.id, t(user.language or "ru", "checkin_question", name=user.first_name or ""))
                key = StorageKey(bot_id=bot.id, chat_id=user.id, user_id=user.id)
                ctx = FSMContext(storage=storage, key=key)
                await ctx.set_state(CheckinPending.waiting)
            except Exception as e:
                logger.warning("Checkin failed for user %s: %s", user.id, e)


def start_scheduler(bot, storage) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _check_and_send_checkins,
        "interval",
        minutes=1,
        args=[bot, storage],
        id="checkin_scheduler",
    )
    scheduler.add_job(
        _check_and_send_digests,
        "interval",
        hours=1,
        args=[bot],
        id="digest_scheduler",
    )
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
