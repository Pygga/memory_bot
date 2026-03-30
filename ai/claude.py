import logging
import os

from groq import Groq, APIError, APITimeoutError

logger = logging.getLogger(__name__)

from db.models import Entry

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def answer_from_diary(question: str, entries: list[Entry], history: list[dict] | None = None) -> str:
    """Ответить на вопрос на основе записей дневника.
    history — предыдущие сообщения диалога [{"role": ..., "content": ...}]
    """
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
                "Опирайся только на записи — не придумывай. Отвечай кратко и по делу."
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
        return response.choices[0].message.content
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in answer_from_diary: %s", e)
        return "Сервис временно недоступен, попробуй чуть позже."


DIGEST_PROMPTS = {
    "brief": (
        "Составь краткий дайджест за {period}. "
        "3-4 пункта, только самое важное. Без воды.\n\nЗаписи:\n{diary_text}"
    ),
    "full": (
        "Составь развёрнутый дайджест за {period}. "
        "Структура: главные темы, общее настроение, важные события, один вывод.\n\nЗаписи:\n{diary_text}"
    ),
    "emotional": (
        "Проанализируй эмоциональное состояние за {period}. "
        "Как менялось настроение? Что беспокоило? Что радовало? Были ли переломные моменты?\n\nЗаписи:\n{diary_text}"
    ),
}


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
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in generate_digest: %s", e)
        return "Не удалось сгенерировать дайджест. Попробуй позже."


def answer_ai(history: list[dict]) -> str:
    """Ответить как чистый AI-ассистент без контекста дневника.
    history — список {"role": "user"/"assistant", "content": "..."}
    """
    messages = [{"role": "system", "content": "Ты умный помощник. Отвечай кратко и по делу."}]
    messages.extend(history[-20:])  # не больше 20 последних сообщений

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        return response.choices[0].message.content
    except (APIError, APITimeoutError) as e:
        logger.error("Groq API error in answer_ai: %s", e)
        return "Сервис временно недоступен, попробуй чуть позже."
