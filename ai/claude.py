import logging
import os
import re

from groq import Groq, APIError, APITimeoutError

logger = logging.getLogger(__name__)

from db.models import Entry

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_FORMAT_RULES = """
Пиши plain text — без markdown и HTML-тегов.
Для списков используй • (символ пули).
Не используй **жирный**, _курсив_, ### заголовки и любые теги.
"""


def _strip_formatting(text: str) -> str:
    """Убирает markdown-разметку, оставляет чистый текст с • для списков"""
    # **bold** и __bold__ → просто текст
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # *italic* и _italic_ → просто текст
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # ### Header → текст без #
    text = re.sub(r"#{1,3}\s+(.+)", r"\1", text)
    # - item и * item → • item
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)
    return text


_TYPE_LABELS = {
    "audio": "голосовое",
    "photo": "фото",
    "text": "текст",
    "video": "видео",
}


def _format_entry(e: Entry) -> str:
    type_label = _TYPE_LABELS.get(e.type.value if hasattr(e.type, "value") else str(e.type), "текст")
    ts = e.created_at.strftime("%d.%m.%Y %H:%M")
    return f"[{ts}, {type_label}] {e.text}"


def answer_from_diary(question: str, entries: list[Entry], history: list[dict] | None = None) -> str:
    """Ответить на вопрос на основе записей дневника."""
    if not entries:
        current_message = f"Вопрос: {question}"
    else:
        diary_text = "\n\n".join(_format_entry(e) for e in entries if e.text)
        current_message = f"Релевантные записи из дневника:\n{diary_text}\n\nВопрос: {question}"

    messages = [
        {
            "role": "system",
            "content": (
                "Ты — ассистент, который анализирует записи личного дневника пользователя.\n"
                "Говори про пользователя: 'ты писал', 'тебя беспокоило', 'ты упоминал'.\n"
                "Опирайся только на записи — не придумывай. Отвечай кратко и по делу.\n\n"
                + _FORMAT_RULES
            ),
        }
    ]

    if history:
        messages.extend(history[-20:])

    messages.append({"role": "user", "content": current_message})

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        return _strip_formatting(response.choices[0].message.content)
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in answer_from_diary: %s", e)
        return "Сервис временно недоступен, попробуй чуть позже."


DIGEST_PROMPTS = {
    "brief": (
        "Составь краткий дайджест за {period}. "
        "3-4 пункта, только самое важное. Без воды.\n\n"
        "Записи:\n{diary_text}"
    ),
    "full": (
        "Составь развёрнутый дайджест за {period}. "
        "Разделы: Главные темы, Настроение, События, Вывод.\n\n"
        "Записи:\n{diary_text}"
    ),
    "emotional": (
        "Проанализируй эмоциональное состояние за {period}. "
        "Разделы: Общий фон, Что беспокоило, Что радовало, Переломные моменты.\n\n"
        "Записи:\n{diary_text}"
    ),
}

_DIGEST_SYSTEM = (
    "Ты анализируешь записи личного дневника и составляешь структурированный дайджест.\n"
    + _FORMAT_RULES
)


def generate_digest(entries: list[Entry], fmt: str = "full", period: str = "неделю") -> str:
    """Сгенерировать дайджест за период"""
    if not entries:
        return "За этот период записей не найдено."

    diary_text = "\n\n".join(_format_entry(e) for e in entries if e.text)

    prompt = DIGEST_PROMPTS.get(fmt, DIGEST_PROMPTS["full"]).format(
        period=period, diary_text=diary_text
    )

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _DIGEST_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return _strip_formatting(response.choices[0].message.content)
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in generate_digest: %s", e)
        return "Не удалось сгенерировать дайджест. Попробуй позже."


def answer_ai(history: list[dict]) -> str:
    """Ответить как чистый AI-ассистент без контекста дневника."""
    messages = [
        {
            "role": "system",
            "content": "Ты умный помощник. Отвечай кратко и по делу.\n\n" + _FORMAT_RULES,
        }
    ]
    messages.extend(history[-20:])

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        return _strip_formatting(response.choices[0].message.content)
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in answer_ai: %s", e)
        return "Сервис временно недоступен, попробуй чуть позже."
