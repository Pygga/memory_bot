import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
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


class MenuState(StatesGroup):
    checkin_time = State()
    digest_time = State()


# ── Keyboards ──────────────────────────────────────────────────────────────


def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌙 Чекин", callback_data="menu:checkin"),
            InlineKeyboardButton(text="📋 Дайджест", callback_data="menu:digest"),
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
    await message.answer("Главное меню:", reply_markup=_main_kb())


@menu_router.callback_query(F.data == "menu:main")
async def cb_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню:", reply_markup=_main_kb())
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
    await call.message.answer("Введи время чекина:\n`21:00 +3`", parse_mode="Markdown")
    await call.answer()


@menu_router.message(MenuState.checkin_time)
async def handle_checkin_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        hour, minute = map(int, parts[0].split(":"))
        utc_offset = int(parts[1].replace("+", ""))
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
    await call.message.answer("Введи время дайджеста:\n`20:00 +3`", parse_mode="Markdown")
    await call.answer()


@menu_router.message(MenuState.digest_time)
async def handle_digest_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        hour = int(parts[0].split(":")[0])
        utc_offset = int(parts[1].replace("+", ""))
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
