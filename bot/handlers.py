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
from db import async_session
from db.models import EntryType
from db.queries import find_similar_entries_not_today, get_or_create_user, save_entry, search_entries

IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

router = Router()


class AIChat(StatesGroup):
    active = State()


class DiaryChat(StatesGroup):
    active = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with async_session() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Я твой личный дневник. Просто напиши что-нибудь или отправь голосовое — я сохраню.\n\n"
        "Чтобы спросить о прошлом, начни сообщение с '?'\n"
        "Например: '? что я делал на прошлой неделе'"
    )


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    await message.answer("Слушаю и записываю...")

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
        await message.answer("Не удалось распознать речь.")
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

    await message.answer(f"Записал 🎤\n_{transcript}_", parse_mode="Markdown")


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    await message.answer("Смотрю на фото...")

    photo = message.photo[-1]  # берём максимальное разрешение
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

    await message.answer(f"Записал 📷\n{description}")


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    doc = message.document
    mime = doc.mime_type or ""

    if mime not in IMAGE_MIMETYPES and mime != "application/pdf":
        await message.answer("Поддерживаю только изображения и PDF.")
        return

    await message.answer("Читаю файл...")

    ext = ".pdf" if mime == "application/pdf" else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, destination=tmp_path)

    try:
        if mime == "application/pdf":
            # Сначала пробуем извлечь текст напрямую
            reader = PdfReader(tmp_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text:
                # Скан — конвертируем в изображения и читаем через OCR
                pages = convert_from_path(tmp_path, dpi=200, first_page=1, last_page=5)
                text = "\n\n".join(
                    pytesseract.image_to_string(page, lang="rus+eng")
                    for page in pages
                ).strip()
            entry_type = EntryType.text
        else:
            # Изображение-файл: OCR для документов, BLIP для фото
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
    await message.answer(f"Записал {icon}\n{text}")


@router.message(F.text == "!=")
async def ai_exit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("AI режим закрыт.")


@router.message(F.text == "!?")
async def diary_exit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Поиск закрыт.")


@router.message(F.text.startswith("?"))
async def diary_enter(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(DiaryChat.active)
    await state.update_data(history=[])

    question = message.text[1:].strip()
    SEARCH_HEADER = "🔍 Поиск по дневнику  |  выход — !?\n\n"

    if not question:
        await message.answer(f"{SEARCH_HEADER}Задавай вопросы — отвечу на основе твоих записей.")
        return

    sent = await message.answer("Ищу в дневнике...")
    async with async_session() as session:
        await get_or_create_user(session, user_id=user_id, username=message.from_user.username, first_name=message.from_user.first_name)
        embedding = get_embedding(question)
        entries = await search_entries(session, user_id, embedding, limit=5)

    answer = answer_from_diary(question, entries)
    history = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    await state.update_data(history=history)
    await sent.edit_text(f"{SEARCH_HEADER}{answer}")


@router.message(DiaryChat.active)
async def diary_chat(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("В режиме дневника поддерживаю только текст. Для выхода — !?")
        return

    user_id = message.from_user.id
    data = await state.get_data()
    history = data.get("history", [])

    sent = await message.answer("Ищу в дневнике...")
    async with async_session() as session:
        await get_or_create_user(session, user_id=user_id, username=message.from_user.username, first_name=message.from_user.first_name)
        embedding = get_embedding(message.text)
        entries = await search_entries(session, user_id, embedding, limit=5)

    answer = answer_from_diary(message.text, entries, history)
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await sent.edit_text(answer)


@router.message(F.text.startswith("="))
async def ai_enter(message: Message, state: FSMContext):
    await state.set_state(AIChat.active)
    await state.update_data(history=[])

    question = message.text[1:].strip()
    if not question:
        await message.answer("AI режим включён. Пиши — отвечу. Чтобы выйти — напиши !=")
        return

    sent = await message.answer("Думаю...")
    history = [{"role": "user", "content": question}]
    answer = answer_ai(history)
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await sent.edit_text(answer)


@router.message(AIChat.active)
async def ai_chat(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("В AI режиме поддерживаю только текст. Для выхода — !=")
        return

    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "user", "content": message.text})

    sent = await message.answer("Думаю...")
    answer = answer_ai(history)
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await sent.edit_text(answer)


@router.message(StateFilter("*"), F.text.in_({
    "🔍 Поиск по дневнику", "🤖 Ассистент", "📋 Дайджест", "🌙 Чекин", "⚙️ Настройки"
}))
async def handle_menu_buttons(message: Message, state: FSMContext):
    from bot.menu import _checkin_kb, _digest_kb, _reply_kb
    await state.clear()
    text = message.text

    if text == "🔍 Поиск по дневнику":
        await state.set_state(DiaryChat.active)
        await state.update_data(history=[])
        await message.answer("🔍 Поиск по дневнику включён. Задавай вопросы — отвечу на основе записей.\nВыход — нажми любую другую кнопку меню.")

    elif text == "🤖 Ассистент":
        await state.set_state(AIChat.active)
        await state.update_data(history=[])
        await message.answer("🤖 Ассистент включён. Пиши — отвечу.\nВыход — нажми любую другую кнопку меню.")

    elif text == "🌙 Чекин":
        async with async_session() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
            kb = _checkin_kb(user.checkin_enabled, user.checkin_hour, user.checkin_minute, user.checkin_utc_offset)
        await message.answer("🌙 Вечерний чекин:", reply_markup=kb)

    elif text == "📋 Дайджест":
        async with async_session() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
            kb = _digest_kb(user.digest_enabled, user.digest_hour, user.digest_utc_offset, user.digest_period, user.digest_format)
        await message.answer("📋 Дайджест:", reply_markup=kb)

    elif text == "⚙️ Настройки":
        await message.answer("Меню открыто 👇", reply_markup=_reply_kb())


@router.message()
async def handle_message(message: Message):
    if not message.text:
        return

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
        await message.answer("Записал в дневник ✓")

        similar = await find_similar_entries_not_today(session, user_id, embedding, limit=1) if len(message.text) > 30 else []
        if similar:
            old = similar[0]
            date_str = old.created_at.strftime("%d.%m.%Y")
            preview = old.text[:150] + ("..." if len(old.text) > 150 else "")
            await message.answer(f"Кстати, {date_str} ты писал похожее:\n\n{preview}")
