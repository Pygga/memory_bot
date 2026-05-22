import asyncio
import os

from dotenv import load_dotenv

load_dotenv()  # Загружаем .env до импорта модулей проекта

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from bot.admin import admin_router
from bot.book_handler import book_router
from bot.checkin import checkin_router, start_scheduler
from bot.handlers import router
from bot.menu import menu_router
from db import init_db


async def main():
    await init_db()

    storage = MemoryStorage()
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await bot.set_my_commands([
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="start", description="Начать"),
        BotCommand(command="book", description="Книга за месяц"),
        BotCommand(command="book_all", description="Полная книга"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="delete_my_data", description="Удалить все данные"),
    ])
    dp = Dispatcher(storage=storage)

    dp.include_router(admin_router)     # Admin commands (ADMIN_ID only)
    dp.include_router(menu_router)     # FSM: MenuState (время чекина/дайджеста)
    dp.include_router(checkin_router)  # FSM: CheckinPending
    dp.include_router(router)
    dp.include_router(book_router)     # Book generation commands

    scheduler = start_scheduler(bot, storage)

    print("Бот запущен...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
