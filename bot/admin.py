import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db import async_session
from db.queries import get_admin_stats, get_recent_users

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

admin_router = Router()


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not _is_admin(message.from_user.id):
        return

    args = message.text.split()[1:]

    async with async_session() as session:
        if args and args[0] == "users":
            users = await get_recent_users(session, limit=10)
            if not users:
                await message.answer("Пользователей нет.")
                return
            lines = []
            for u in users:
                name = u.first_name or "—"
                username = f"@{u.username}" if u.username else "—"
                date = u.created_at.strftime("%d.%m.%Y")
                lines.append(f"• {name} ({username}) — {date} — `{u.id}`")
            await message.answer("👥 Последние пользователи:\n\n" + "\n".join(lines), parse_mode="Markdown")
            return

        stats = await get_admin_stats(session)

    text = (
        "📊 *Статистика*\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📝 Записей: {stats['total_entries']}\n"
        f"🆕 Новых сегодня: {stats['new_today']}\n"
        f"🔥 Активных за неделю: {stats['active_week']}\n\n"
        "Команды:\n"
        "`/admin` — статистика\n"
        "`/admin users` — последние пользователи"
    )
    await message.answer(text, parse_mode="Markdown")
