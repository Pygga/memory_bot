from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class EntryType(enum.Enum):
    text = "text"
    audio = "audio"
    photo = "photo"
    video = "video"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    language: Mapped[str] = mapped_column(String(8), default="ru", server_default="ru")

    checkin_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    checkin_hour: Mapped[int] = mapped_column(Integer, default=21, server_default="21")
    checkin_minute: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    checkin_utc_offset: Mapped[int] = mapped_column(Integer, default=5, server_default="5")

    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    digest_period: Mapped[str] = mapped_column(String(16), default="week", server_default="week")
    digest_format: Mapped[str] = mapped_column(String(16), default="full", server_default="full")
    digest_hour: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    digest_utc_offset: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    digest_day: Mapped[int] = mapped_column(Integer, default=6, server_default="6")

    entries: Mapped[list["Entry"]] = relationship(back_populates="user")


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    type: Mapped[EntryType] = mapped_column(Enum(EntryType))

    # Текст записи (для audio/video — транскрипт, для photo — описание)
    text: Mapped[str | None] = mapped_column(Text)

    # Краткое резюме для отображения
    summary: Mapped[str | None] = mapped_column(Text)

    # Ссылка на файл в R2 (только для audio/photo/video)
    file_url: Mapped[str | None] = mapped_column(String(512))

    # Вектор для семантического поиска (1536 измерений — стандарт для Claude)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="entries")

    __table_args__ = (
        Index("ix_entries_user_id", "user_id"),
        Index("ix_entries_user_created", "user_id", "created_at"),
    )
