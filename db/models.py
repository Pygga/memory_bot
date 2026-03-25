from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
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
