from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Entry, EntryType, User


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    """Получить пользователя или создать при первом обращении"""
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
    return user


async def save_entry(
    session: AsyncSession,
    user_id: int,
    type: EntryType,
    text: str | None = None,
    summary: str | None = None,
    file_url: str | None = None,
    embedding: list[float] | None = None,
) -> Entry:
    """Сохранить новую запись в дневник"""
    entry = Entry(
        user_id=user_id,
        type=type,
        text=text,
        summary=summary,
        file_url=file_url,
        embedding=embedding,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def search_entries(
    session: AsyncSession,
    user_id: int,
    query_embedding: list[float],
    limit: int = 5,
) -> list[Entry]:
    """Найти записи по смысловой близости через векторный поиск"""
    result = await session.execute(
        select(Entry)
        .where(Entry.user_id == user_id)
        .where(Entry.embedding.isnot(None))
        .order_by(Entry.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_entries(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> list[Entry]:
    """Получить последние записи пользователя"""
    result = await session.execute(
        select(Entry)
        .where(Entry.user_id == user_id)
        .order_by(Entry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
