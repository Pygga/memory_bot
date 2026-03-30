import logging
import os
import re

from groq import Groq, APIError, APITimeoutError

logger = logging.getLogger(__name__)

from db.models import Entry

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_FORMAT_RULES = """
Форматируй ответ для Telegram HTML:
• Используй <b>текст</b> для заголовков и ключевых слов
• Используй • для списков (просто символ, без тегов)
• Используй <i>текст</i> для дат и второстепенных деталей
• Не используй markdown (**text**, ##, ---), только HTML-теги выше
• Не используй <ul>, <li>, <br> и другие HTML-теги кроме <b> и <i>
"""


def _md_to_html(text: str) -> str:
    """Конвертирует остатки markdown в HTML на случай если модель не послушалась"""
    # **bold** или __bold__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # *italic* или _italic_
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # ### Header → <b>Header</b>
    text = re.sub(r"#{1,3}\s+(.+)", r"<b>\1</b>", text)
    # - item → • item
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)
    return text


def answer_from_diary(question: str, entries: list[Entry], history: list[dict] | None = None) -> str:
    """Ответить на вопрос на основе записей дневника."""
    if not entries:
        current_message = f"Вопрос: {question}"
    else:
        diary_text = "\n\n".join(
            f"[{e.created_at.strftime('%d.%m.%Y')}] {e.text}"
            for e in entries
            if e.text
        )
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
        return _md_to_html(response.choices[0].message.content)
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
        "Разделы: <b>Главные темы</b>, <b>Настроение</b>, <b>События</b>, <b>Вывод</b>.\n\n"
        "Записи:\n{diary_text}"
    ),
    "emotional": (
        "Проанализируй эмоциональное состояние за {period}. "
        "Разделы: <b>Общий фон</b>, <b>Что беспокоило</b>, <b>Что радовало</b>, <b>Переломные моменты</b>.\n\n"
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

    diary_text = "\n\n".join(
        f"[{e.created_at.strftime('%d.%m.%Y')}] {e.text}"
        for e in entries
        if e.text
    )

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
        return _md_to_html(response.choices[0].message.content)
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
        return _md_to_html(response.choices[0].message.content)
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in answer_ai: %s", e)
        return "Сервис временно недоступен, попробуй чуть позже."
