import os
from groq import Groq

from db.models import Entry

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def answer_from_diary(question: str, entries: list[Entry]) -> str:
    """Ответить на вопрос пользователя от лица его прошлого 'я'"""
    if not entries:
        return "Я не нашёл в дневнике записей, связанных с твоим вопросом."

    diary_text = "\n\n".join(
        f"[{e.created_at.strftime('%d.%m.%Y')}] {e.text}"
        for e in entries
        if e.text
    )

    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": f"""Ты — личный дневник пользователя. Отвечай кратко и по делу, основываясь только на записях.
  Не добавляй эмоций и украшений, которых нет в записях. Ты — прошлое 'я' пользователя. Учитывай стиль общения пользователя и его фразочки
Отвечай от первого лица, как будто вспоминаешь прожитые моменты.

Записи из дневника:
{diary_text}

Вопрос пользователя: {question}""",
            }
        ],
    )

    return response.choices[0].message.content
