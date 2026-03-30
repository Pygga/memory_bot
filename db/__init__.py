from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from .models import Base
import os

engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """Создаёт все таблицы при старте бота"""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавляем колонки чекина если их ещё нет
        for stmt in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS checkin_enabled BOOLEAN DEFAULT false",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS checkin_hour INTEGER DEFAULT 21",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS checkin_minute INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS checkin_utc_offset INTEGER DEFAULT 5",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_enabled BOOLEAN DEFAULT false",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_period VARCHAR(16) DEFAULT 'week'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_format VARCHAR(16) DEFAULT 'full'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_hour INTEGER DEFAULT 20",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_utc_offset INTEGER DEFAULT 5",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_day INTEGER DEFAULT 6",
        ]:
            await conn.execute(text(stmt))
