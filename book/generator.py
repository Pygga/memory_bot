"""
Генератор PDF-книги воспоминаний с красивым дизайном.
Использует WeasyPrint и Jinja2 для создания книг в формате A5.
"""
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

from db.models import Entry, EntryType


# Иконки для типов записей
TYPE_ICONS = {
    EntryType.text: "📝",
    EntryType.audio: "🎤",
    EntryType.photo: "📷",
    EntryType.video: "🎬",
}

# Пути к шрифтам
FONT_PATHS = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/TTF/DejaVuSerif.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ],
}


def find_font(paths: list[str]) -> Optional[str]:
    """Найти первый существующий шрифт из списка."""
    return next((p for p in paths if os.path.exists(p)), None)


def extract_tags(text: str) -> tuple[str, list[str]]:
    """Извлечь теги из текста (формат #тег)."""
    import re
    tags = re.findall(r'#(\w+)', text)
    clean_text = re.sub(r'#\w+', '', text).strip()
    return clean_text, list(set(tags))


def group_entries_by_period(
    entries: list[Entry],
    period: str = "week"
) -> list[dict]:
    """
    Сгруппировать записи по периодам (недели или месяцы).
    
    Args:
        entries: Список записей, отсортированных по дате
        period: 'week' или 'month'
    
    Returns:
        Список глав с записями
    """
    if not entries:
        return []
    
    chapters = []
    current_chapter = None
    
    for entry in entries:
        local_dt = entry.created_at.astimezone(timezone.utc)
        
        if period == "month":
            chapter_key = local_dt.strftime("%Y-%m")
            chapter_title = local_dt.strftime("%B %Y")
            date_range = local_dt.strftime("%B %Y")
        else:  # week
            # Номер недели
            iso_cal = local_dt.isocalendar()
            chapter_key = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
            chapter_title = f"Week {iso_cal[1]}, {iso_cal[0]}"
            
            # Начало и конец недели
            start_of_week = local_dt - timedelta(days=local_dt.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            date_range = f"{start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m.%Y')}"
        
        # Перевод названий месяцев на русский
        month_names_ru = {
            "January": "Январь", "February": "Февраль", "March": "Март",
            "April": "Апрель", "May": "Май", "June": "Июнь",
            "July": "Июль", "August": "Август", "September": "Сентябрь",
            "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь"
        }
        
        for en, ru in month_names_ru.items():
            chapter_title = chapter_title.replace(en, ru)
            date_range = date_range.replace(en, ru)
        
        if current_chapter is None or current_chapter["key"] != chapter_key:
            if current_chapter is not None:
                chapters.append(current_chapter)
            
            current_chapter = {
                "key": chapter_key,
                "title": chapter_title,
                "date_range": date_range,
                "entries": [],
                "page": len(chapters) + 1,
            }
        
        # Обработка записи
        clean_text, tags = extract_tags(entry.text or "")
        
        entry_data = {
            "time": local_dt.strftime("%H:%M"),
            "type_icon": TYPE_ICONS.get(entry.type, "📝"),
            "text": clean_text,
            "tags": tags,
            "photo_url": entry.file_url if entry.type == EntryType.photo else None,
        }
        
        current_chapter["entries"].append(entry_data)
    
    if current_chapter is not None:
        chapters.append(current_chapter)
    
    return chapters


def generate_memory_book(
    entries: list[Entry],
    owner_name: str,
    lang: str = "ru",
    period: str = "week",
    output_path: Optional[str] = None
) -> str:
    """
    Сгенерировать PDF-книгу воспоминаний.
    
    Args:
        entries: Список записей пользователя
        owner_name: Имя владельца
        lang: Язык ('ru' или 'en')
        period: Группировка ('week' или 'month')
        output_path: Путь для сохранения (если None, создается временный файл)
    
    Returns:
        Путь к созданному PDF файлу
    """
    from datetime import timedelta
    
    # Тексты для разных языков
    texts = {
        "ru": {
            "book_title": "Книга Воспоминаний",
            "subtitle": "Хроника жизни и мыслей",
            "toc_title": "Содержание",
            "no_entries": "В этом периоде пока нет записей",
            "endnote": "«Память — это единственное место, где время останавливается»",
            "generated": "Сгенерировано",
        },
        "en": {
            "book_title": "Memory Book",
            "subtitle": "Chronicle of Life and Thoughts",
            "toc_title": "Table of Contents",
            "no_entries": "No entries in this period yet",
            "endnote": "\"Memory is the only place where time stands still\"",
            "generated": "Generated",
        }
    }
    
    t = texts.get(lang, texts["ru"])
    
    # Определение даты диапазона
    if entries:
        first_date = min(e.created_at for e in entries)
        last_date = max(e.created_at for e in entries)
        first_str = first_date.strftime("%d.%m.%Y")
        last_str = last_date.strftime("%d.%m.%Y")
        date_range = f"{first_str} — {last_str}"
    else:
        date_range = ""
    
    # Группировка записей
    chapters = group_entries_by_period(entries, period)
    
    # Подготовка шаблона
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("book_template.html")
    
    # Рендеринг HTML
    html_content = template.render(
        lang=lang,
        title=t["book_title"],
        book_title=t["book_title"],
        subtitle=t["subtitle"],
        author_name=owner_name or "Anonymous",
        date_range=date_range,
        toc_title=t["toc_title"],
        chapters=chapters,
        no_entries_text=t["no_entries"],
        endnote=t["endnote"],
        generated_at=f"{t['generated']}: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    )
    
    # Поиск шрифтов
    font_regular = find_font(FONT_PATHS["regular"])
    font_bold = find_font(FONT_PATHS["bold"])
    
    # Настройка CSS для шрифтов
    if font_regular and font_bold:
        css_content = f"""
        @font-face {{
            font-family: 'DejaVu Serif';
            src: url('{font_regular}');
            font-weight: normal;
        }}
        @font-face {{
            font-family: 'DejaVu Serif';
            src: url('{font_bold}');
            font-weight: bold;
        }}
        body {{
            font-family: 'DejaVu Serif', serif !important;
        }}
        """
        css = CSS(string=css_content)
    else:
        css = CSS(string="")
    
    # Генерация PDF
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = tmp.name
    
    html = HTML(string=html_content, base_url=".")
    html.write_pdf(output_path, stylesheets=[css])
    
    return output_path


# Простая функция для тестирования
if __name__ == "__main__":
    # Тестовые данные
    now = datetime.now(timezone.utc)
    test_entries = [
        Entry(
            id=1,
            user_id=123,
            type=EntryType.text,
            text="Сегодня был прекрасный день! #счастье #день",
            created_at=now,
        ),
        Entry(
            id=2,
            user_id=123,
            type=EntryType.audio,
            text="Записал свои мысли о будущем #мысли",
            created_at=now - timedelta(hours=2),
        ),
    ]
    
    pdf_path = generate_memory_book(
        entries=test_entries,
        owner_name="Test User",
        lang="ru",
        period="week"
    )
    
    print(f"PDF создан: {pdf_path}")
    print(f"Размер файла: {os.path.getsize(pdf_path)} байт")
