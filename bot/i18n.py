STRINGS: dict[str, dict[str, str]] = {
    # ── Handlers ──────────────────────────────────────────────────────────────
    "listening": {
        "ru": "Слушаю и записываю...",
        "en": "Listening and saving...",
    },
    "speech_failed": {
        "ru": "Не удалось распознать речь.",
        "en": "Could not recognize speech.",
    },
    "saved_audio": {
        "ru": "Записал 🎤\n_{transcript}_",
        "en": "Saved 🎤\n_{transcript}_",
    },
    "looking_photo": {
        "ru": "Смотрю на фото...",
        "en": "Looking at the photo...",
    },
    "saved_photo": {
        "ru": "Записал 📷\n{description}",
        "en": "Saved 📷\n{description}",
    },
    "reading_file": {
        "ru": "Читаю файл...",
        "en": "Reading file...",
    },
    "unsupported_file": {
        "ru": "Поддерживаю только изображения и PDF.",
        "en": "Only images and PDF are supported.",
    },
    "saved_file": {
        "ru": "Записал {icon}\n{text}",
        "en": "Saved {icon}\n{text}",
    },
    "searching_diary": {
        "ru": "Ищу в дневнике...",
        "en": "Searching diary...",
    },
    "thinking": {
        "ru": "Думаю...",
        "en": "Thinking...",
    },
    "saved_entry": {
        "ru": "Записал в дневник ✓",
        "en": "Saved to diary ✓",
    },
    "similar_entry": {
        "ru": "Кстати, {date} ты писал похожее:\n\n{preview}",
        "en": "By the way, on {date} you wrote something similar:\n\n{preview}",
    },

    # ── Menu ──────────────────────────────────────────────────────────────────
    "main_menu": {
        "ru": "Главное меню:",
        "en": "Main menu:",
    },
    "search_title": {
        "ru": "🔍 Поиск по дневнику",
        "en": "🔍 Diary search",
    },
    "ai_title": {
        "ru": "🤖 Ассистент",
        "en": "🤖 Assistant",
    },
    "digest_title": {
        "ru": "📋 Дайджест",
        "en": "📋 Digest",
    },
    "checkin_title": {
        "ru": "🌙 Чекин",
        "en": "🌙 Check-in",
    },
    "settings_title": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
    },
    "search_prompt": {
        "ru": "🔍 Поиск по дневнику\n\nЗадавай вопросы — отвечу на основе твоих записей.",
        "en": "🔍 Diary search\n\nAsk questions — I'll answer based on your entries.",
    },
    "search_exit": {
        "ru": "← Выйти из поиска",
        "en": "← Exit search",
    },
    "ai_prompt": {
        "ru": "🤖 Ассистент\n\nПиши — отвечу на любой вопрос.",
        "en": "🤖 Assistant\n\nWrite anything — I'll answer any question.",
    },
    "ai_exit": {
        "ru": "← Выйти из ассистента",
        "en": "← Exit assistant",
    },
    "back": {
        "ru": "← Назад",
        "en": "← Back",
    },
    "settings_menu": {
        "ru": "⚙️ Настройки:",
        "en": "⚙️ Settings:",
    },
    "language_btn": {
        "ru": "🌐 Язык: RU",
        "en": "🌐 Language: EN",
    },

    # ── Checkin ───────────────────────────────────────────────────────────────
    "checkin_menu": {
        "ru": "⚙️ Настройки / 🌙 Чекин",
        "en": "⚙️ Settings / 🌙 Check-in",
    },
    "checkin_enabled": {
        "ru": "✅ Чекин включён",
        "en": "✅ Check-in enabled",
    },
    "checkin_disabled": {
        "ru": "❌ Чекин выключен",
        "en": "❌ Check-in disabled",
    },
    "checkin_toggled_on": {
        "ru": "Включён ✅",
        "en": "Enabled ✅",
    },
    "checkin_toggled_off": {
        "ru": "Выключен ❌",
        "en": "Disabled ❌",
    },
    "checkin_time_prompt": {
        "ru": "Отправь геолокацию — определю часовой пояс автоматически.\nИли введи вручную: `21:00 +3`",
        "en": "Send your location — I'll detect the timezone automatically.\nOr enter manually: `21:00 +3`",
    },
    "checkin_time_error": {
        "ru": "Неверный формат. Пример: `21:00 +3`",
        "en": "Wrong format. Example: `21:00 +3`",
    },
    "checkin_question": {
        "ru": "{name}, добрый вечер 🌙 Поделись впечатлениями о сегодняшнем дне?",
        "en": "{name}, good evening 🌙 How was your day?",
    },
    "checkin_saved": {
        "ru": "Записал ✓",
        "en": "Saved ✓",
    },
    "checkin_page_title": {
        "ru": "🌙 Чекин",
        "en": "🌙 Check-in",
    },
    "checkin_write_now": {
        "ru": "✏️ Написать сейчас",
        "en": "✏️ Write now",
    },
    "checkin_no_entries": {
        "ru": "Записей чекина пока нет.",
        "en": "No check-in entries yet.",
    },
    "checkin_recent": {
        "ru": "Последние записи:\n\n{entries}",
        "en": "Recent entries:\n\n{entries}",
    },
    "checkin_write_prompt": {
        "ru": "{name}, как прошёл день? 🌙",
        "en": "{name}, how was your day? 🌙",
    },

    # ── Digest ────────────────────────────────────────────────────────────────
    "digest_menu": {
        "ru": "⚙️ Настройки / 📋 Дайджест",
        "en": "⚙️ Settings / 📋 Digest",
    },
    "digest_get_now": {
        "ru": "📨 Получить сейчас",
        "en": "📨 Get now",
    },
    "digest_period_week": {
        "ru": "Период: неделя",
        "en": "Period: weekly",
    },
    "digest_period_month": {
        "ru": "Период: месяц",
        "en": "Period: monthly",
    },
    "digest_format_brief": {
        "ru": "Формат: краткий",
        "en": "Format: brief",
    },
    "digest_format_full": {
        "ru": "Формат: полный",
        "en": "Format: full",
    },
    "digest_format_emotional": {
        "ru": "Формат: эмоции",
        "en": "Format: emotional",
    },
    "digest_time_prompt": {
        "ru": "Отправь геолокацию — определю часовой пояс автоматически.\nИли введи вручную: `20:00 +3`",
        "en": "Send your location — I'll detect the timezone automatically.\nOr enter manually: `20:00 +3`",
    },
    "digest_time_error": {
        "ru": "Неверный формат. Пример: `20:00 +3`",
        "en": "Wrong format. Example: `20:00 +3`",
    },
    "digest_generating": {
        "ru": "Генерирую дайджест...",
        "en": "Generating digest...",
    },
    "digest_no_entries": {
        "ru": "За этот период записей нет.",
        "en": "No entries for this period.",
    },
    "digest_result": {
        "ru": "📋 Дайджест за {period}:\n\n{text}",
        "en": "📋 Digest for the {period}:\n\n{text}",
    },
    "digest_period_label_week": {
        "ru": "неделю",
        "en": "week",
    },
    "digest_period_label_month": {
        "ru": "месяц",
        "en": "month",
    },

    # ── Digest toggle labels ──────────────────────────────────────────────────
    "digest_enabled": {
        "ru": "✅ Дайджест включён",
        "en": "✅ Digest enabled",
    },
    "digest_disabled": {
        "ru": "❌ Дайджест выключен",
        "en": "❌ Digest disabled",
    },

    # ── Buttons ───────────────────────────────────────────────────────────────
    "settings_back": {
        "ru": "← Настройки",
        "en": "← Settings",
    },
    "time_checkin_btn": {
        "ru": "Время: {time} (UTC{sign}{offset})",
        "en": "Time: {time} (UTC{sign}{offset})",
    },
    "time_digest_btn": {
        "ru": "Время: {time} (UTC{sign}{offset})",
        "en": "Time: {time} (UTC{sign}{offset})",
    },

    # ── Geolocation ───────────────────────────────────────────────────────────
    "location_btn": {
        "ru": "📍 Отправить геолокацию",
        "en": "📍 Share location",
    },
    "location_detected": {
        "ru": "Часовой пояс определён: UTC{sign}{offset}",
        "en": "Timezone detected: UTC{sign}{offset}",
    },
    "location_failed": {
        "ru": "Не удалось определить часовой пояс. Введи вручную: `{example}`",
        "en": "Could not detect timezone. Enter manually: `{example}`",
    },

    # ── Export ────────────────────────────────────────────────────────────────
    "export_btn": {
        "ru": "📤 Экспорт в PDF",
        "en": "📤 Export to PDF",
    },
    "export_generating": {
        "ru": "Генерирую PDF...",
        "en": "Generating PDF...",
    },
    "export_empty": {
        "ru": "Записей пока нет — нечего экспортировать.",
        "en": "No entries yet — nothing to export.",
    },
    "export_filename": {
        "ru": "дневник.pdf",
        "en": "diary.pdf",
    },

    # ── Rate limit ────────────────────────────────────────────────────────────
    "rate_limit": {
        "ru": "📝 Ты уже сделал {limit} записей сегодня — это дневной лимит. Возвращайся завтра!",
        "en": "📝 You've reached the daily limit of {limit} entries. Come back tomorrow!",
    },

    # ── Invite ────────────────────────────────────────────────────────────────
    "invite_wrong": {
        "ru": "❌ Неверный код. Попробуй ещё раз.",
        "en": "❌ Wrong code. Try again.",
    },

    # ── Onboarding ────────────────────────────────────────────────────────────
    "onboard_1": {
        "ru": (
            "👋 Привет, {name}!\n\n"
            "Я твой личный дневник.\n\n"
            "Просто пиши мне — мысли, события, идеи. "
            "Или отправь голосовое, фото, PDF — сохраню всё.\n\n"
            "⬤ ○ ○"
        ),
        "en": (
            "👋 Hey, {name}!\n\n"
            "I'm your personal diary.\n\n"
            "Just write to me — thoughts, events, ideas. "
            "Or send a voice message, photo, PDF — I'll save everything.\n\n"
            "⬤ ○ ○"
        ),
    },
    "onboard_1_return": {
        "ru": (
            "👋 Привет!\n\n"
            "Я твой личный дневник.\n\n"
            "Просто пиши мне — мысли, события, идеи. "
            "Или отправь голосовое, фото, PDF — сохраню всё.\n\n"
            "⬤ ○ ○"
        ),
        "en": (
            "👋 Hey!\n\n"
            "I'm your personal diary.\n\n"
            "Just write to me — thoughts, events, ideas. "
            "Or send a voice message, photo, PDF — I'll save everything.\n\n"
            "⬤ ○ ○"
        ),
    },
    "onboard_2": {
        "ru": (
            "🔍 Умный поиск по прошлому\n\n"
            "Спроси меня о любом периоде жизни — "
            "найду нужные записи и отвечу на их основе.\n\n"
            "«что я делал в январе?»\n"
            "«как я себя чувствовал на прошлой неделе?»\n\n"
            "○ ⬤ ○"
        ),
        "en": (
            "🔍 Smart search through the past\n\n"
            "Ask me about any period of your life — "
            "I'll find the relevant entries and answer based on them.\n\n"
            "\"what did I do in January?\"\n"
            "\"how did I feel last week?\"\n\n"
            "○ ⬤ ○"
        ),
    },
    "onboard_3": {
        "ru": (
            "✨ Что ещё умею\n\n"
            "🌙 Вечерний чекин — напишу сам, ты только ответь\n"
            "📋 Дайджест — обзор твоей жизни за неделю\n"
            "🤖 Ассистент — поговори или задай любой вопрос\n\n"
            "○ ○ ⬤"
        ),
        "en": (
            "✨ What else I can do\n\n"
            "🌙 Evening check-in — I'll write first, just reply\n"
            "📋 Digest — a summary of your week\n"
            "🤖 Assistant — chat or ask anything\n\n"
            "○ ○ ⬤"
        ),
    },
    "onboard_next": {
        "ru": "Дальше →",
        "en": "Next →",
    },
    "onboard_back": {
        "ru": "← Назад",
        "en": "← Back",
    },
    "onboard_start": {
        "ru": "Начать →",
        "en": "Start →",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in ("ru", "en") else "ru"
    text = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("ru", key)
    return text.format(**kwargs) if kwargs else text
