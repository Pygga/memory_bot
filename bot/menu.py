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
from bot.i18n import t
from db import async_session
from db.queries import (
    get_entries_for_period,
    get_or_create_user,
    update_checkin_settings,
    update_digest_settings,
    update_language,
)

logger = logging.getLogger(__name__)
menu_router = Router()


async def _get_lang(user_id: int) -> str:
    from db.models import User
    async with async_session() as session:
        user = await session.get(User, user_id)
        return user.language if user else "ru"


def _location_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "location_btn"), request_location=True)]],
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


def _main_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "search_title"), callback_data="menu:search")],
        [
            InlineKeyboardButton(text=t(lang, "ai_title"), callback_data="menu:ai"),
            InlineKeyboardButton(text=t(lang, "digest_title"), callback_data="menu:digest"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "checkin_title"), callback_data="menu:checkin"),
            InlineKeyboardButton(text=t(lang, "settings_title"), callback_data="menu:settings"),
        ],
    ])


def _checkin_kb(lang: str, enabled: bool, hour: int, minute: int, utc_offset: int) -> InlineKeyboardMarkup:
    toggle = t(lang, "checkin_enabled") if enabled else t(lang, "checkin_disabled")
    sign = "+" if utc_offset >= 0 else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="menu:checkin:toggle")],
        [InlineKeyboardButton(
            text=f"🕐 {hour:02d}:{minute:02d} (UTC{sign}{utc_offset})",
            callback_data="menu:checkin:time",
        )],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:main")],
    ])


PERIOD_KEYS = {"week": "digest_period_week", "month": "digest_period_month"}
PERIOD_NEXT = {"week": "month", "month": "week"}
FORMAT_KEYS = {"brief": "digest_format_brief", "full": "digest_format_full", "emotional": "digest_format_emotional"}
FORMAT_NEXT = {"brief": "full", "full": "emotional", "emotional": "brief"}


def _digest_kb(lang: str, enabled: bool, hour: int, utc_offset: int, period: str, fmt: str) -> InlineKeyboardMarkup:
    toggle = t(lang, "checkin_enabled") if enabled else t(lang, "checkin_disabled")
    sign = "+" if utc_offset >= 0 else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="menu:digest:toggle")],
        [InlineKeyboardButton(text=t(lang, "digest_get_now"), callback_data="menu:digest:now")],
        [InlineKeyboardButton(text=t(lang, PERIOD_KEYS.get(period, "digest_period_week")), callback_data="menu:digest:period")],
        [InlineKeyboardButton(text=t(lang, FORMAT_KEYS.get(fmt, "digest_format_full")), callback_data="menu:digest:format")],
        [InlineKeyboardButton(
            text=f"🕐 {hour:02d}:00 (UTC{sign}{utc_offset})",
            callback_data="menu:digest:time",
        )],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:main")],
    ])


# ── Main menu ──────────────────────────────────────────────────────────────


@menu_router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await main_menu_message(message)


async def main_menu_message(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    tmp = await message.answer(".", reply_markup=ReplyKeyboardRemove())
    await tmp.delete()
    await message.answer(t(lang, "main_menu"), reply_markup=_main_kb(lang))


async def onboarding_step_1(message: Message, first_name: str) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дальше →  /  Next →", callback_data="onboard:lang")],
    ])
    await message.answer(
        f"👋 Привет, {first_name}! / Hey, {first_name}!\n\n"
        "Выбери язык / Choose language:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="onboard:lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="onboard:lang:en"),
            ],
        ]),
    )


@menu_router.callback_query(F.data.in_({"onboard:lang:ru", "onboard:lang:en"}))
async def cb_onboard_lang(call: CallbackQuery):
    lang = call.data.split(":")[-1]
    async with async_session() as session:
        await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.first_name)
        await update_language(session, call.from_user.id, lang)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "onboard_next"), callback_data="onboard:2")],
    ])
    await call.message.edit_text(t(lang, "onboard_1", name=call.from_user.first_name), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "onboard:2")
async def cb_onboard_2(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "onboard_back"), callback_data="onboard:1"),
            InlineKeyboardButton(text=t(lang, "onboard_next"), callback_data="onboard:3"),
        ],
    ])
    await call.message.edit_text(t(lang, "onboard_2"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "onboard:1")
async def cb_onboard_1(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "onboard_next"), callback_data="onboard:2")],
    ])
    await call.message.edit_text(t(lang, "onboard_1_return"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "onboard:3")
async def cb_onboard_3(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "onboard_back"), callback_data="onboard:2"),
            InlineKeyboardButton(text=t(lang, "onboard_start"), callback_data="onboard:done"),
        ],
    ])
    await call.message.edit_text(t(lang, "onboard_3"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "onboard:done")
async def cb_onboard_done(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    await call.message.edit_text(t(lang, "main_menu"), reply_markup=_main_kb(lang))
    await call.answer()


@menu_router.callback_query(F.data == "menu:main")
async def cb_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await _get_lang(call.from_user.id)
    await call.message.edit_text(t(lang, "main_menu"), reply_markup=_main_kb(lang))
    await call.answer()


@menu_router.callback_query(F.data == "menu:search")
async def cb_search(call: CallbackQuery, state: FSMContext):
    from bot.handlers import DiaryChat
    lang = await _get_lang(call.from_user.id)
    await state.set_state(DiaryChat.active)
    await state.update_data(history=[])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "search_exit"), callback_data="menu:main")],
    ])
    await call.message.edit_text(t(lang, "search_prompt"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:ai")
async def cb_ai(call: CallbackQuery, state: FSMContext):
    from bot.handlers import AIChat
    lang = await _get_lang(call.from_user.id)
    await state.set_state(AIChat.active)
    await state.update_data(history=[])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "ai_exit"), callback_data="menu:main")],
    ])
    await call.message.edit_text(t(lang, "ai_prompt"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:settings")
async def cb_settings(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    next_lang = "en" if lang == "ru" else "ru"
    lang_label = "🌐 RU → EN" if lang == "ru" else "🌐 EN → RU"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "checkin_title"), callback_data="menu:checkin")],
        [InlineKeyboardButton(text=t(lang, "digest_title"), callback_data="menu:digest")],
        [InlineKeyboardButton(text=lang_label, callback_data=f"menu:lang:{next_lang}")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:main")],
    ])
    await call.message.edit_text(t(lang, "settings_menu"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data.startswith("menu:lang:"))
async def cb_lang(call: CallbackQuery):
    new_lang = call.data.split(":")[-1]
    async with async_session() as session:
        await update_language(session, call.from_user.id, new_lang)
    next_lang = "en" if new_lang == "ru" else "ru"
    lang_label = "🌐 RU → EN" if new_lang == "ru" else "🌐 EN → RU"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(new_lang, "checkin_title"), callback_data="menu:checkin")],
        [InlineKeyboardButton(text=t(new_lang, "digest_title"), callback_data="menu:digest")],
        [InlineKeyboardButton(text=lang_label, callback_data=f"menu:lang:{next_lang}")],
        [InlineKeyboardButton(text=t(new_lang, "back"), callback_data="menu:main")],
    ])
    await call.message.edit_text(t(new_lang, "settings_menu"), reply_markup=kb)
    await call.answer()


# ── Checkin ────────────────────────────────────────────────────────────────


@menu_router.callback_query(F.data == "menu:checkin")
async def cb_checkin(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        kb = _checkin_kb(lang, user.checkin_enabled, user.checkin_hour, user.checkin_minute, user.checkin_utc_offset)
    await call.message.edit_text(t(lang, "checkin_menu"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:checkin:toggle")
async def cb_checkin_toggle(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_enabled = not user.checkin_enabled
        hour, minute, offset = user.checkin_hour, user.checkin_minute, user.checkin_utc_offset
        await update_checkin_settings(session, call.from_user.id, enabled=new_enabled)
    await call.message.edit_reply_markup(reply_markup=_checkin_kb(lang, new_enabled, hour, minute, offset))
    await call.answer(t(lang, "checkin_toggled_on") if new_enabled else t(lang, "checkin_toggled_off"))


@menu_router.callback_query(F.data == "menu:checkin:time")
async def cb_checkin_time(call: CallbackQuery, state: FSMContext):
    lang = await _get_lang(call.from_user.id)
    await state.set_state(MenuState.checkin_time)
    await call.message.answer(
        t(lang, "checkin_time_prompt"),
        parse_mode="Markdown",
        reply_markup=_location_kb(lang),
    )
    await call.answer()


@menu_router.message(MenuState.checkin_time, F.text)
async def handle_checkin_time(message: Message, state: FSMContext):
    lang = await _get_lang(message.from_user.id)
    try:
        parts = message.text.strip().split()
        hour, minute = map(int, parts[0].split(":"))
        utc_offset = int(parts[1])
        assert 0 <= hour <= 23 and 0 <= minute <= 59 and -12 <= utc_offset <= 14
    except Exception:
        await message.answer(t(lang, "checkin_time_error"), parse_mode="Markdown")
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled = user.checkin_enabled
        await update_checkin_settings(session, message.from_user.id, hour=hour, minute=minute, utc_offset=utc_offset)

    await state.clear()
    await message.answer(t(lang, "checkin_menu"), reply_markup=_checkin_kb(lang, enabled, hour, minute, utc_offset))


@menu_router.message(MenuState.checkin_time, F.location)
async def handle_checkin_location(message: Message, state: FSMContext):
    lang = await _get_lang(message.from_user.id)
    utc_offset = _utc_offset_from_location(message.location.latitude, message.location.longitude)
    if utc_offset is None:
        await message.answer(
            t(lang, "location_failed", example="21:00 +3"),
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
    await message.answer(t(lang, "location_detected", sign=sign, offset=utc_offset), reply_markup=ReplyKeyboardRemove())
    await message.answer(t(lang, "checkin_menu"), reply_markup=_checkin_kb(lang, enabled, hour, minute, utc_offset))


# ── Digest ─────────────────────────────────────────────────────────────────


@menu_router.callback_query(F.data == "menu:digest")
async def cb_digest(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        kb = _digest_kb(lang, user.digest_enabled, user.digest_hour, user.digest_utc_offset, user.digest_period, user.digest_format)
    await call.message.edit_text(t(lang, "digest_menu"), reply_markup=kb)
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:toggle")
async def cb_digest_toggle(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_enabled = not user.digest_enabled
        hour, offset, period, fmt = (
            user.digest_hour, user.digest_utc_offset, user.digest_period, user.digest_format
        )
        await update_digest_settings(session, call.from_user.id, enabled=new_enabled)
    await call.message.edit_reply_markup(reply_markup=_digest_kb(lang, new_enabled, hour, offset, period, fmt))
    await call.answer(t(lang, "checkin_toggled_on") if new_enabled else t(lang, "checkin_toggled_off"))


@menu_router.callback_query(F.data == "menu:digest:period")
async def cb_digest_period(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
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
    await call.message.edit_reply_markup(reply_markup=_digest_kb(lang, enabled, hour, offset, new_period, fmt))
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:format")
async def cb_digest_format(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        new_fmt = FORMAT_NEXT[user.digest_format]
        enabled, hour, offset, period = (
            user.digest_enabled, user.digest_hour, user.digest_utc_offset, user.digest_period
        )
        await update_digest_settings(session, call.from_user.id, format=new_fmt)
    await call.message.edit_reply_markup(reply_markup=_digest_kb(lang, enabled, hour, offset, period, new_fmt))
    await call.answer()


@menu_router.callback_query(F.data == "menu:digest:time")
async def cb_digest_time(call: CallbackQuery, state: FSMContext):
    lang = await _get_lang(call.from_user.id)
    await state.set_state(MenuState.digest_time)
    await call.message.answer(
        t(lang, "digest_time_prompt"),
        parse_mode="Markdown",
        reply_markup=_location_kb(lang),
    )
    await call.answer()


@menu_router.message(MenuState.digest_time, F.text)
async def handle_digest_time(message: Message, state: FSMContext):
    lang = await _get_lang(message.from_user.id)
    try:
        parts = message.text.strip().split()
        hour = int(parts[0].split(":")[0])
        utc_offset = int(parts[1])
        assert 0 <= hour <= 23 and -12 <= utc_offset <= 14
    except Exception:
        await message.answer(t(lang, "digest_time_error"), parse_mode="Markdown")
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.first_name
        )
        enabled, period, fmt = user.digest_enabled, user.digest_period, user.digest_format
        await update_digest_settings(session, message.from_user.id, hour=hour, utc_offset=utc_offset)

    await state.clear()
    await message.answer(t(lang, "digest_menu"), reply_markup=_digest_kb(lang, enabled, hour, utc_offset, period, fmt))


@menu_router.message(MenuState.digest_time, F.location)
async def handle_digest_location(message: Message, state: FSMContext):
    lang = await _get_lang(message.from_user.id)
    utc_offset = _utc_offset_from_location(message.location.latitude, message.location.longitude)
    if utc_offset is None:
        await message.answer(
            t(lang, "location_failed", example="20:00 +3"),
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
    await message.answer(t(lang, "location_detected", sign=sign, offset=utc_offset), reply_markup=ReplyKeyboardRemove())
    await message.answer(t(lang, "digest_menu"), reply_markup=_digest_kb(lang, enabled, hour, utc_offset, period, fmt))


@menu_router.callback_query(F.data == "menu:digest:now")
async def cb_digest_now(call: CallbackQuery):
    lang = await _get_lang(call.from_user.id)
    await call.answer(t(lang, "digest_generating"))
    async with async_session() as session:
        user = await get_or_create_user(
            session, call.from_user.id, call.from_user.username, call.from_user.first_name
        )
        days = 7 if user.digest_period == "week" else 30
        period_label = t(lang, "digest_period_label_week") if user.digest_period == "week" else t(lang, "digest_period_label_month")
        fmt = user.digest_format
        entries = await get_entries_for_period(session, call.from_user.id, days=days)

    if not entries:
        await call.message.answer(t(lang, "digest_no_entries"))
        return

    sent = await call.message.answer(t(lang, "digest_generating"))
    text = generate_digest(entries, fmt=fmt, period=period_label)
    await sent.edit_text(t(lang, "digest_result", period=period_label, text=text))
