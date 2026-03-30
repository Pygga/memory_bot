import tempfile
from datetime import timezone

from fpdf import FPDF

from db.models import Entry, EntryType

_TYPE_ICON = {
    EntryType.text: "",
    EntryType.audio: "[voice] ",
    EntryType.photo: "[photo] ",
    EntryType.video: "[video] ",
}


def generate_diary_pdf(entries: list[Entry], owner_name: str, lang: str = "ru") -> str:
    """Генерирует PDF со всеми записями, возвращает путь к временному файлу"""
    title = "Мой дневник" if lang == "ru" else "My Diary"
    no_entries = "Записей пока нет." if lang == "ru" else "No entries yet."

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # fpdf2 includes DejaVu which covers Cyrillic
    pdf.add_font("DejaVu", style="", fname="DejaVuSansCondensed.ttf")
    pdf.add_font("DejaVu", style="B", fname="DejaVuSansCondensed-Bold.ttf")

    # Title
    pdf.set_font("DejaVu", style="B", size=18)
    pdf.cell(0, 12, title, align="C", new_x="LMARGIN", new_y="NEXT")

    if owner_name:
        pdf.set_font("DejaVu", size=11)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, owner_name, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    pdf.ln(6)

    if not entries:
        pdf.set_font("DejaVu", size=12)
        pdf.cell(0, 10, no_entries)
    else:
        prev_date = None
        for entry in entries:
            local_dt = entry.created_at.astimezone(timezone.utc)
            date_str = local_dt.strftime("%d.%m.%Y")
            time_str = local_dt.strftime("%H:%M")

            # Date separator
            if date_str != prev_date:
                if prev_date is not None:
                    pdf.ln(4)
                pdf.set_font("DejaVu", style="B", size=11)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 8, date_str, new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                prev_date = date_str

            # Entry text
            icon = _TYPE_ICON.get(entry.type, "")
            text = (icon + (entry.text or "")).strip()

            pdf.set_font("DejaVu", size=10)
            pdf.set_text_color(140, 140, 140)
            pdf.cell(0, 5, time_str, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("DejaVu", size=11)
            pdf.multi_cell(0, 6, text)
            pdf.ln(3)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    pdf.output(tmp.name)
    return tmp.name
