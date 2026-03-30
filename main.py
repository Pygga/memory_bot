import asyncio
import os

from dotenv import load_dotenv

load_dotenv()  # Загружаем .env до импорта модулей проекта

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.checkin import checkin_router, start_scheduler
from bot.handlers import router
from bot.menu import menu_router
from db import init_db


async def main():
    await init_db()

    storage = MemoryStorage()
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=storage)

    dp.include_router(menu_router)     # FSM: MenuState (время чекина/дайджеста)
    dp.include_router(checkin_router)  # FSM: CheckinPending
    dp.include_router(router)

    scheduler = start_scheduler(bot, storage)

    print("Бот запущен...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
