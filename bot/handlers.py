import os
import tempfile

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, Voice
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader

from ai.claude import answer_ai, answer_from_diary
from ai.embeddings import get_embedding
from ai.transcriber import transcribe_audio
from ai.vision import describe_image
from bot.i18n import t
from db import async_session
from db.models import EntryType
from db.queries import find_similar_entries_not_today, get_or_create_user, save_entry, search_entries

IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_INVITE_CODES: set[str] = {
    c.strip() for c in os.getenv("INVITE_CODE", "").split(",") if c.strip()
}

router = Router()


class InviteState(StatesGroup):
    waiting = State()


class AIChat(StatesGroup):
    active = State()


class DiaryChat(StatesGroup):
    active = State()


async def _get_lang(user_id: int) -> str:
    from db.models import User
    async with async_session() as session:
        user = await session.get(User, user_id)
        return user.language if user else "ru"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    from bot.menu import onboarding_step_1, main_menu_message
    from db.models import User
    async with async_session() as session:
        existing = await session.get(User, message.from_user.id)

    await state.clear()

    if existing:
        await main_menu_message(message)
        return

    # New user — check invite code if required
    if _INVITE_CODES:
        await state.set_state(InviteState.waiting)
        name = message.from_user.first_name or ""
        await message.answer(
            f"👋 {name}\n\n"
            "🔐 Бот в закрытом доступе. Введи инвайт-код:\n"
            "_Bot is invite-only. Enter your invite code:_",
            parse_mode="Markdown",
        )
        return

    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
    await onboarding_step_1(message, message.from_user.first_name or "")


@router.message(InviteState.waiting)
async def handle_invite_code(message: Message, state: FSMContext):
    if not message.text:
        return

    if message.text.strip() not in _INVITE_CODES:
        await message.answer(t("ru", "invite_wrong"))
        return

    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
    await state.clear()
    from bot.menu import onboarding_step_1
    await onboarding_step_1(message, message.from_user.first_name or "")


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    lang = await _get_lang(message.from_user.id)
    await message.answer(t(lang, "listening"))

    voice: Voice = message.voice
    file = await bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    await bot.download_file(file.file_path, destination=tmp_path)

    try:
        transcript = transcribe_audio(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not transcript:
        await message.answer(t(lang, "speech_failed"))
        return

    embedding = get_embedding(transcript)
    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await save_entry(
            session,
            user_id=message.from_user.id,
            type=EntryType.audio,
            text=transcript,
            embedding=embedding,
        )

    await message.answer(t(lang, "saved_audio", transcript=transcript), parse_mode="Markdown")


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    lang = await _get_lang(message.from_user.id)
    await message.answer(t(lang, "looking_photo"))

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    await bot.download_file(file.file_path, destination=tmp_path)

    try:
        description = describe_image(tmp_path)
    finally:
        os.unlink(tmp_path)

    if message.caption:
        description = f"{message.caption}. {description}"

    embedding = get_embedding(description)
    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await save_entry(
            session,
            user_id=message.from_user.id,
            type=EntryType.photo,
            text=description,
            embedding=embedding,
        )

    await message.answer(t(lang, "saved_photo", description=description))


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    lang = await _get_lang(message.from_user.id)
    doc = message.document
    mime = doc.mime_type or ""

    if mime not in IMAGE_MIMETYPES and mime != "application/pdf":
        await message.answer(t(lang, "unsupported_file"))
        return

    await message.answer(t(lang, "reading_file"))

    ext = ".pdf" if mime == "application/pdf" else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, destination=tmp_path)

    try:
        if mime == "application/pdf":
            reader = PdfReader(tmp_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text:
                pages = convert_from_path(tmp_path, dpi=200, first_page=1, last_page=5)
                text = "\n\n".join(
                    pytesseract.image_to_string(page, lang="rus+eng")
                    for page in pages
                ).strip()
            entry_type = EntryType.text
        else:
            from PIL import Image
            img = Image.open(tmp_path)
            ocr_text = pytesseract.image_to_string(img, lang="rus+eng").strip()
            text = ocr_text if len(ocr_text) > 30 else describe_image(tmp_path)
            entry_type = EntryType.photo
    finally:
        os.unlink(tmp_path)

    if message.caption:
        text = f"{message.caption}. {text}"

    embedding = get_embedding(text)
    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await save_entry(
            session,
            user_id=message.from_user.id,
            type=entry_type,
            text=text,
            embedding=embedding,
        )

    icon = "📄" if mime == "application/pdf" else "📷"
    await message.answer(t(lang, "saved_file", icon=icon, text=text))


@router.message(DiaryChat.active)
async def diary_chat(message: Message, state: FSMContext):
    if not message.text:
        return

    lang = await _get_lang(message.from_user.id)
    user_id = message.from_user.id
    data = await state.get_data()
    history = data.get("history", [])

    sent = await message.answer(t(lang, "searching_diary"))
    async with async_session() as session:
        await get_or_create_user(session, user_id=user_id, username=message.from_user.username, first_name=message.from_user.first_name)
        embedding = get_embedding(message.text)
        entries = await search_entries(session, user_id, embedding, limit=5)

    answer = answer_from_diary(message.text, entries, history)
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await sent.edit_text(answer)


@router.message(AIChat.active)
async def ai_chat(message: Message, state: FSMContext):
    if not message.text:
        return

    lang = await _get_lang(message.from_user.id)
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "user", "content": message.text})

    sent = await message.answer(t(lang, "thinking"))
    answer = answer_ai(history)
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await sent.edit_text(answer)


@router.message(StateFilter(None))
async def handle_message(message: Message):
    if not message.text:
        return

    lang = await _get_lang(message.from_user.id)
    user_id = message.from_user.id

    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        embedding = get_embedding(message.text)
        await save_entry(
            session,
            user_id=user_id,
            type=EntryType.text,
            text=message.text,
            embedding=embedding,
        )
        await message.answer(t(lang, "saved_entry"))

        similar = await find_similar_entries_not_today(session, user_id, embedding, limit=1) if len(message.text) > 30 else []
        if similar:
            old = similar[0]
            date_str = old.created_at.strftime("%d.%m.%Y")
            preview = old.text[:150] + ("..." if len(old.text) > 150 else "")
            await message.answer(t(lang, "similar_entry", date=date_str, preview=preview))
