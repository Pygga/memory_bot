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
