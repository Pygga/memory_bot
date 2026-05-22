"""
Обработчики команд для книги воспоминаний.
"""
import os
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from book.generator import generate_memory_book
from bot.i18n import t
from db import async_session
from db.models import User
from db.queries import get_entries_for_book, get_or_create_user

book_router = Router()


async def _get_lang(user_id: int) -> str:
    """Получить язык пользователя."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        return user.language if user else "ru"


@book_router.message(Command("book"))
async def cmd_book(message: Message):
    """Команда /book - создать книгу воспоминаний за последний месяц."""
    lang = await _get_lang(message.from_user.id)
    
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
        entries = await get_entries_for_book(session, message.from_user.id, days=30)
    
    if not entries:
        await message.answer(t(lang, "book_empty"))
        return
    
    # Отправляем сообщение о генерации
    sent = await message.answer(t(lang, "book_generating"))
    
    try:
        # Генерируем книгу
        pdf_path = generate_memory_book(
            entries=entries,
            owner_name=user.first_name or "",
            lang=lang,
            period="week",
        )
        
        # Отправляем файл
        with open(pdf_path, "rb") as f:
            await message.answer_document(
                document=BufferedInputFile(f.read(), filename=t(lang, "book_filename")),
                caption=f"📚 {t(lang, 'book_title') if lang == 'ru' else 'Memory Book'}\n"
                        f"За период: {entries[0].created_at.strftime('%d.%m')} - {entries[-1].created_at.strftime('%d.%m.%Y')}"
            )
        
        # Удаляем сообщение о генерации
        await sent.delete()
        
    except Exception as e:
        await sent.edit_text(f"❌ Ошибка при создании книги: {str(e)}")
    
    finally:
        # Удаляем временный файл
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


@book_router.message(Command("book_month"))
async def cmd_book_month(message: Message):
    """Команда /book_month - создать книгу воспоминаний за последние 90 дней."""
    lang = await _get_lang(message.from_user.id)
    
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
        entries = await get_entries_for_book(session, message.from_user.id, days=90)
    
    if not entries:
        await message.answer(t(lang, "book_empty"))
        return
    
    sent = await message.answer(t(lang, "book_generating"))
    
    try:
        pdf_path = generate_memory_book(
            entries=entries,
            owner_name=user.first_name or "",
            lang=lang,
            period="month",
        )
        
        with open(pdf_path, "rb") as f:
            await message.answer_document(
                document=BufferedInputFile(f.read(), filename=t(lang, "book_filename")),
                caption=f"📚 Книга за 3 месяца\n"
                        f"За период: {entries[0].created_at.strftime('%d.%m')} - {entries[-1].created_at.strftime('%d.%m.%Y')}"
            )
        
        await sent.delete()
        
    except Exception as e:
        await sent.edit_text(f"❌ Ошибка при создании книги: {str(e)}")
    
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


@book_router.message(Command("book_all"))
async def cmd_book_all(message: Message):
    """Команда /book_all - создать книгу со всеми воспоминаниями."""
    lang = await _get_lang(message.from_user.id)
    
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
        # Получаем все записи (365 дней)
        entries = await get_entries_for_book(session, message.from_user.id, days=365)
    
    if not entries:
        await message.answer(t(lang, "book_empty"))
        return
    
    sent = await message.answer(t(lang, "book_generating"))
    
    try:
        pdf_path = generate_memory_book(
            entries=entries,
            owner_name=user.first_name or "",
            lang=lang,
            period="month",
        )
        
        with open(pdf_path, "rb") as f:
            await message.answer_document(
                document=BufferedInputFile(f.read(), filename=t(lang, "book_filename")),
                caption=f"📚 Полная книга воспоминаний\n"
                        f"За период: {entries[0].created_at.strftime('%d.%m.%Y')} - {entries[-1].created_at.strftime('%d.%m.%Y')}"
            )
        
        await sent.delete()
        
    except Exception as e:
        await sent.edit_text(f"❌ Ошибка при создании книги: {str(e)}")
    
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


@book_router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help - справка по боту."""
    lang = await _get_lang(message.from_user.id)
    
    help_text_ru = """
📖 **Память - Бот дневник**

Я помогу тебе сохранить воспоминания и создать из них красивую книгу!

**Что я умею:**
✍️ Принимать текстовые записи
🎤 Транскрибировать голосовые сообщения
📷 Описывать и сохранять фото
📄 Читать PDF файлы

**Команды:**
/menu - Главное меню
/book - Книга за последний месяц
/book_month - Книга за 3 месяца  
/book_all - Полная книга воспоминаний
/export - Простой экспорт в PDF
/delete_my_data - Удалить все данные

**Как использовать:**
1. Просто пиши мне свои мысли
2. Добавляй #теги через решетку
3. Отправь /book когда хочешь книгу

#память #дневник #воспоминания
"""
    
    help_text_en = """
📖 **Memory - Diary Bot**

I'll help you preserve memories and create a beautiful book!

**What I can do:**
✍️ Accept text entries
🎤 Transcribe voice messages
📷 Describe and save photos
📄 Read PDF files

**Commands:**
/menu - Main menu
/book - Book for last month
/book_month - Book for 3 months
/book_all - Complete memory book
/export - Simple PDF export
/delete_my_data - Delete all data

**How to use:**
1. Just write your thoughts to me
2. Add #tags using hash symbol
3. Send /book when you want a book

#memory #diary #thoughts
"""
    
    await message.answer(
        help_text_ru if lang == "ru" else help_text_en,
        parse_mode="Markdown"
    )
