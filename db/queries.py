from datetime import datetime, timedelta, timezone

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


async def find_similar_entries_not_today(
    session: AsyncSession,
    user_id: int,
    query_embedding: list[float],
    limit: int = 1,
    max_distance: float = 0.4,
    min_text_len: int = 30,
) -> list[Entry]:
    """Найти похожие записи из прошлых дней (не сегодня).
    Возвращает только записи с реальным сходством (max_distance) и достаточной длиной текста.
    """
    from sqlalchemy import func
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(Entry)
        .where(Entry.user_id == user_id)
        .where(Entry.embedding.isnot(None))
        .where(Entry.created_at < today_start)
        .where(Entry.embedding.cosine_distance(query_embedding) < max_distance)
        .where(func.length(Entry.text) > min_text_len)
        .order_by(Entry.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_digest_users(session: AsyncSession) -> list[User]:
    """Получить всех пользователей с включённым дайджестом"""
    result = await session.execute(
        select(User).where(User.digest_enabled == True)
    )
    return list(result.scalars().all())


async def update_digest_settings(
    session: AsyncSession,
    user_id: int,
    enabled: bool | None = None,
    period: str | None = None,
    format: str | None = None,
    hour: int | None = None,
    utc_offset: int | None = None,
    day: int | None = None,
) -> None:
    """Обновить настройки дайджеста для пользователя"""
    user = await session.get(User, user_id)
    if user is None:
        return
    if enabled is not None:
        user.digest_enabled = enabled
    if period is not None:
        user.digest_period = period
    if format is not None:
        user.digest_format = format
    if hour is not None:
        user.digest_hour = hour
    if utc_offset is not None:
        user.digest_utc_offset = utc_offset
    if day is not None:
        user.digest_day = day
    await session.commit()


async def get_entries_for_period(
    session: AsyncSession,
    user_id: int,
    days: int,
) -> list[Entry]:
    """Получить записи за последние N дней"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(Entry)
        .where(Entry.user_id == user_id)
        .where(Entry.created_at >= since)
        .order_by(Entry.created_at.asc())
    )
    return list(result.scalars().all())


async def get_checkin_users(session: AsyncSession) -> list[User]:
    """Получить всех пользователей с включённым чекином"""
    result = await session.execute(
        select(User).where(User.checkin_enabled == True)
    )
    return list(result.scalars().all())


async def update_checkin_settings(
    session: AsyncSession,
    user_id: int,
    enabled: bool | None = None,
    hour: int | None = None,
    minute: int | None = None,
    utc_offset: int | None = None,
) -> None:
    """Обновить настройки чекина для пользователя"""
    user = await session.get(User, user_id)
    if user is None:
        return
    if enabled is not None:
        user.checkin_enabled = enabled
    if hour is not None:
        user.checkin_hour = hour
    if minute is not None:
        user.checkin_minute = minute
    if utc_offset is not None:
        user.checkin_utc_offset = utc_offset
    await session.commit()


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
