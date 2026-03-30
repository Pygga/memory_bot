import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from ai.claude import generate_digest
from db import async_session
from db.queries import (
    get_entries_for_period,
    get_or_create_user,
    update_checkin_settings,
    update_digest_settings,
)

logger = logging.getLogger(__name__)
menu_router = Router()


def _location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _utc_offset_from_location(lat: float, lng: float) -> int | None:
    from timezonefinder import TimezoneFinder
    from zoneinfo import ZoneInfo
    tf = TimezoneFinder()
    tz_str = tf.timezone_at(lat=lat, lng=lng)
    if not tz_str:
        return None
    now = datetime.now(ZoneInfo(tz_str))
    return int(now.utcoffset().total_seconds() / 3600)


class MenuState(StatesGroup):
    checkin_time = State()
    digest_time = State()


# ── Keyboards ──────────────────────────────────────────────────────────────


def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по дневнику", callback_data="menu:search")],
        [
            InlineKeyboardButton(text="🤖 Ассистент", callback_data="menu:ai"),
            InlineKeyboardButton(text="📋 Дайджест", callback_data="menu:digest"),
        ],
        [
            InlineKeyboardButton(text="🌙 Чекин", callback_data="menu:checkin"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
    ])


def _checkin_kb(enabled: bool, hour: int, minute: int, utc_offset: int) -> InlineKeyboardMarkup:
    toggle = "✅ Включён" if enabled else "❌ Выключен"
    sign = "+" if utc_offset >= 0 else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="menu:checkin:toggle")],
        [InlineKeyboardButton(
            text=f"🕐 {hour:02d}:{minute:02d} (UTC{sign}{utc_offset})",
            callback_data="menu:checkin:time",
        )],
        [InlineKeyboardButton(text="← Назад", callback_data="menu:main")],
    ])


PERIOD_LABELS = {"week": "📅 Раз в неделю", "month": "📅 Раз в месяц"}
PERIOD_NEXT = {"week": "month", "month": "week"}
FORMAT_LABELS = {"brief": "📝 Краткий", "full": "📄 Полный", "emotional": "💬 Эмоции"}
FORMAT_NEXT = {"brief": "full", "full": "emotional", "emotional": "brief"}


def _digest_kb(enabled: bool, hour: int, utc_offset: int, period: str, fmt: str) -> InlineKeyboardMarkup:
    toggle = "✅ Включён" if enabled else "❌ Выключен"
    sign = "+" if utc_offset >= 0 else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="menu:digest:toggle")],
        [InlineKeyboardButton(text="📨 Получить сейчас", callback_data="menu:digest:now")],
        [InlineKeyboardButton(text=PERIOD_LABELS.get(period, period), callback_data="menu:digest:period")],
        [InlineKeyboardButton(text=FORMAT_LABELS.get(fmt, fmt), callback_data="menu:digest:format")],
        [InlineKeyboardButton(
            text=f"🕐 {hour:02d}:00 (UTC{sign}{utc_offset})",
            callback_data="menu:digest:time",
        )],
        [InlineKeyboardButton(text="← Назад", callback_data="menu:main")],
    ])


# ── Main menu ──────────────────────────────────────────────────────────────


@menu_router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await main_menu_message(message)


async def main_menu_message(message: Message) -> None:
    tmp = await message.answer(".", reply_markup=ReplyKeyboardRemove())
    await tmp.delete()
    await message.answer("Главное меню:", reply_markup=_main_kb())


async def onboarding_step_1(message: Message, first_name: str) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дальше →", callback_data="onboard:2")],
    ])
    await message.answer(
        f"👋 Привет, {first_name}!\n\n"
        "Я твой личный дневник.\n\n"
        "Просто пиши мне — мысли, события, идеи. "
        "Или отправь голосовое, фото, PDF — сохраню всё.\n\n"
        "⬤ ○ ○",
        reply_markup=kb,
    )


@menu_router.callback_query(F.data == "onboard:2")
async def cb_onboard_2(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="← Назад", callback_data="onboard:1"),
            InlineKeyboardButton(text="Дальше →", callback_data="onboard:3"),
        ],
    ])
    await call.message.edit_text(
        "🔍 Умный поиск по прошлому\n\n"
        "Спроси меня о любом периоде жизни — "
        "найду нужные записи и отвечу на их основе.\n\n"
        "«что я делал в январе?»\n"
        "«как я себя чувствовал на прошлой неделе?»\n\n"
        "○ ⬤ ○",
        reply_markup=kb,
    )
    await call.answer()


@menu_router.callback_query(F.data == "onboard:1")
async def cb_onboard_1(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дальше →", callback_data="onboard:2")],
    ])
    await call.message.edit_text(
        "👋 Привет!\n\n"
        "Я твой личный дневник.\n\n"
        "Просто пиши мне — мысли, события, идеи. "
        "Или отправь голосовое, фото, PDF — сохраню всё.\n\n"
        "⬤ ○ ○",
        reply_markup=kb,
    )
    await call.answer()


@menu_router.callback_query(F.data == "onboard:3")
async def cb_onboard_3(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="← Назад", callback_data="onboard:2"),
            InlineKeyboardButton(text="Начать →", callback_data="onboard:done"),
        ],
    ])
    await call.message.edit_text(
        "✨ Что ещё умею\n\n"
        "🌙 Вечерний чекин — напишу сам, ты только ответь\n"
        "📋 Дайджест — обзор твоей жизни за неделю\n"
        "🤖 Ассистент — поговори или задай любой вопрос\n\n"
        "○ ○ ⬤",
        reply_markup=kb,
    )
    await call.answer()


@menu_router.callback_query(F.data == "onboard:done")
async def cb_onboard_done(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=_main_kb())
    await call.answer()


@menu_router.callback_query(F.data == "menu:main")
async def cb_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню:", reply_markup=_main_kb())
    await call.answer()


@menu_router.callback_query(F.data == "menu:search")
async def cb_search(call: CallbackQuery, state: FSMContext):
    from bot.handlers import DiaryChat
    await state.set_state(DiaryChat.active)
    await state.update_data(history=[])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Выйти из поиска", callback_data="menu:main")],
    ])
    await call.message.edit_text(
        "🔍 Поиск по дневнику\n\n"
        "Задавай вопросы — отвечу на основе твоих записей.",
        reply_markup=kb,
    )
    await call.answer()


@menu_router.callback_query(F.data == "menu:ai")
async def cb_ai(call: CallbackQuery, state: FSMContext):
    from bot.handlers import AIChat
    await state.set_state(AIChat.active)
    await state.update_data(history=[])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Выйти из ассистента", callback_data="menu:main")],
    ])
    await call.message.edit_text(
        "🤖 Ассистент\n\n"
        "Пиши — отвечу на любой вопрос.",
        reply_markup=kb,
    )
    await call.answer()


@menu_router.callback_query(F.data == "menu:settings")
async def cb_settings(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌙 Чекин", callback_data="menu:checkin")],
        [InlineKeyboardButton(text="📋 Дайджест", callback_data="menu:digest")],
        [InlineKeyboardButton(text="← Назад", callback_data="menu:main")],
    ])
    await call.message.edit_text("⚙️ Настройки:", reply_markup=kb)
    await call.answer()


# ── Checkin ────────────────────────────────────────────────────────────────


@menu_router.callback_query(F.data == "menu:checkin")
async def cb_checkin(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        kb = _checkin_kb(
            user.checkin_enabled, user.checkin_hour,
            user.checkin_minute, user.checkin_utc_offset,
        )
    await call.message.edit_text("🌙 Вечерний чекин:", reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:checkin:toggle")
async def cb_checkin_toggle(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_enabled = not user.checkin_enabled
        hour, minute, offset = user.checkin_hour, user.checkin_minute, user.checkin_utc_offset
        await update_checkin_settings(session, call.from_user.id, enabled=new_enabled)
    await call.message.edit_reply_markup(reply_markup=_checkin_kb(new_enabled, hour, minute, offset))
    await call.answer("Включён ✅" if new_enabled else "Выключен ❌")


@menu_router.callback_query(F.data == "menu:checkin:time")
async def cb_checkin_time(call: CallbackQuery, state: FSMContext):
    await state.set_state(MenuState.checkin_time)
    await call.message.answer(
        "Отправь геолокацию — определю часовой пояс автоматически.\n"
        "Или введи вручную: `21:00 +3`",
        parse_mode="Markdown",
        reply_markup=_location_kb(),
    )
    await call.answer()


@menu_router.message(MenuState.checkin_time, F.text)
async def handle_checkin_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        hour, minute = map(int, parts[0].split(":"))
        utc_offset = int(parts[1])
        assert 0 <= hour <= 23 and 0 <= minute <= 59 and -12 <= utc_offset <= 14
    except Exception:
        await message.answer("Неверный формат. Пример: `21:00 +3`", parse_mode="Markdown")
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled = user.checkin_enabled
        await update_checkin_settings(session, message.from_user.id, hour=hour, minute=minute, utc_offset=utc_offset)

    await state.clear()
    await message.answer(
        "🌙 Вечерний чекин:",
        reply_markup=_checkin_kb(enabled, hour, minute, utc_offset),
    )


@menu_router.message(MenuState.checkin_time, F.location)
async def handle_checkin_location(message: Message, state: FSMContext):
    utc_offset = _utc_offset_from_location(message.location.latitude, message.location.longitude)
    if utc_offset is None:
        await message.answer(
            "Не удалось определить часовой пояс. Введи вручную: `21:00 +3`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled, hour, minute = user.checkin_enabled, user.checkin_hour, user.checkin_minute
        await update_checkin_settings(session, message.from_user.id, utc_offset=utc_offset)

    await state.clear()
    sign = "+" if utc_offset >= 0 else ""
    await message.answer(
        f"Часовой пояс определён: UTC{sign}{utc_offset}",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("🌙 Вечерний чекин:", reply_markup=_checkin_kb(enabled, hour, minute, utc_offset))


# ── Digest ─────────────────────────────────────────────────────────────────


@menu_router.callback_query(F.data == "menu:digest")
async def cb_digest(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        kb = _digest_kb(
            user.digest_enabled, user.digest_hour, user.digest_utc_offset,
            user.digest_period, user.digest_format,
        )
    await call.message.edit_text("📋 Дайджест:", reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:toggle")
async def cb_digest_toggle(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_enabled = not user.digest_enabled
        hour, offset, period, fmt = (
            user.digest_hour, user.digest_utc_offset, user.digest_period, user.digest_format
        )
        await update_digest_settings(session, call.from_user.id, enabled=new_enabled)
    await call.message.edit_reply_markup(reply_markup=_digest_kb(new_enabled, hour, offset, period, fmt))
    await call.answer("Включён ✅" if new_enabled else "Выключен ❌")


@menu_router.callback_query(F.data == "menu:digest:period")
async def cb_digest_period(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_period = PERIOD_NEXT[user.digest_period]
        new_day = 6 if new_period == "week" else 1
        enabled, hour, offset, fmt = (
            user.digest_enabled, user.digest_hour, user.digest_utc_offset, user.digest_format
        )
        await update_digest_settings(session, call.from_user.id, period=new_period, day=new_day)
    await call.message.edit_reply_markup(reply_markup=_digest_kb(enabled, hour, offset, new_period, fmt))
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:format")
async def cb_digest_format(call: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_fmt = FORMAT_NEXT[user.digest_format]
        enabled, hour, offset, period = (
            user.digest_enabled, user.digest_hour, user.digest_utc_offset, user.digest_period
        )
        await update_digest_settings(session, call.from_user.id, format=new_fmt)
    await call.message.edit_reply_markup(reply_markup=_digest_kb(enabled, hour, offset, period, new_fmt))
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:time")
async def cb_digest_time(call: CallbackQuery, state: FSMContext):
    await state.set_state(MenuState.digest_time)
    await call.message.answer(
        "Отправь геолокацию — определю часовой пояс автоматически.\n"
        "Или введи вручную: `20:00 +3`",
        parse_mode="Markdown",
        reply_markup=_location_kb(),
    )
    await call.answer()


@menu_router.message(MenuState.digest_time, F.text)
async def handle_digest_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        hour = int(parts[0].split(":")[0])
        utc_offset = int(parts[1])
        assert 0 <= hour <= 23 and -12 <= utc_offset <= 14
    except Exception:
        await message.answer("Неверный формат. Пример: `20:00 +3`", parse_mode="Markdown")
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled, period, fmt = user.digest_enabled, user.digest_period, user.digest_format
        await update_digest_settings(session, message.from_user.id, hour=hour, utc_offset=utc_offset)

    await state.clear()
    await message.answer(
        "📋 Дайджест:",
        reply_markup=_digest_kb(enabled, hour, utc_offset, period, fmt),
    )


@menu_router.message(MenuState.digest_time, F.location)
async def handle_digest_location(message: Message, state: FSMContext):
    utc_offset = _utc_offset_from_location(message.location.latitude, message.location.longitude)
    if utc_offset is None:
        await message.answer(
            "Не удалось определить часовой пояс. Введи вручную: `20:00 +3`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled, period, fmt = user.digest_enabled, user.digest_period, user.digest_format
        hour = user.digest_hour
        await update_digest_settings(session, message.from_user.id, utc_offset=utc_offset)

    await state.clear()
    sign = "+" if utc_offset >= 0 else ""
    await message.answer(
        f"Часовой пояс определён: UTC{sign}{utc_offset}",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("📋 Дайджест:", reply_markup=_digest_kb(enabled, hour, utc_offset, period, fmt))


@menu_router.callback_query(F.data == "menu:digest:now")
async def cb_digest_now(call: CallbackQuery):
    await call.answer("Генерирую...")
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        days = 7 if user.digest_period == "week" else 30
        period_label = "неделю" if user.digest_period == "week" else "месяц"
        fmt = user.digest_format
        entries = await get_entries_for_period(session, call.from_user.id, days=days)

    if not entries:
        await call.message.answer("За этот период записей нет.")
        return

    sent = await call.message.answer("Генерирую дайджест...")
    text = generate_digest(entries, fmt=fmt, period=period_label)
    await sent.edit_text(f"📋 Дайджест за {period_label}:\n\n{text}")


