import asyncio
import os

from dotenv import load_dotenv

load_dotenv()  # Загружаем .env до импорта модулей проекта

from aiogram import Bot, Dispatcher
from bot.handlers import router
from db import init_db


async def main():
    await init_db()

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
