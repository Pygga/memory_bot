import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db import async_session
from db.queries import get_admin_stats, get_entries_with_embeddings, get_recent_users

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

        if args and args[0] == "clusters":
            user_id = int(args[1]) if len(args) > 1 else message.from_user.id
            entries = await get_entries_with_embeddings(session, user_id)
            if len(entries) < 4:
                await message.answer("Недостаточно записей для кластеризации (нужно минимум 4).")
                return
            from ai.clustering import cluster_entries, get_cluster_samples
            labels, n_clusters = cluster_entries(entries)
            samples = get_cluster_samples(entries, labels, n_clusters)
            lines = []
            for cluster_id, cluster_entries_ in samples.items():
                lines.append(f"*Тема {cluster_id + 1}* ({labels.count(cluster_id)} записей):")
                for e in cluster_entries_:
                    preview = (e.text or "")[:80].replace("\n", " ")
                    lines.append(f"  • {e.created_at.strftime('%d.%m')} {preview}…")
            await message.answer(
                f"🧩 Кластеризация: {n_clusters} тем, {len(entries)} записей\n\n" + "\n".join(lines),
                parse_mode="Markdown",
            )
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
        "`/admin users` — последние пользователи\n"
        "`/admin clusters [user_id]` — кластеры записей"
    )
    await message.answer(text, parse_mode="Markdown")
