# Memory Bot - Бот дневник с генерацией книг воспоминаний

Telegram-бот для сохранения воспоминаний и автоматической генерации красивых PDF-книг.

## Возможности

### Типы воспоминаний
- ✍️ **Текстовые записи** - просто напишите боту
- 🎤 **Голосовые сообщения** - автоматическая транскрипция через Groq Whisper
- 📷 **Фотографии** - описание через компьютерное зрение
- 📄 **PDF файлы** - извлечение текста

### Генерация книг
- 📚 **Красивый дизайн** - обложка, оглавление, главы по неделям/месяцам
- 🏷️ **Теги** - автоматическое извлечение #тегов из текста
- 📅 **Периоды** - книги за месяц, 3 месяца или все воспоминания
- 🌐 **Двуязычность** - русский и английский языки

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать работу с ботом |
| `/menu` | Главное меню |
| `/book` | Книга воспоминаний за последний месяц |
| `/book_month` | Книга за 3 месяца |
| `/book_all` | Полная книга со всеми воспоминаниями |
| `/export` | Простой экспорт в PDF (список записей) |
| `/help` | Справка по боту |
| `/delete_my_data` | Удалить все данные |

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd memory_bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

Создайте файл `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://memorybot:memorybot_password@localhost:5432/memorybot
GROQ_API_KEY=your_groq_api_key
REDIS_URL=redis://localhost:6379/0
```

### 4. Запуск PostgreSQL и Redis (Docker)

```bash
docker-compose up -d postgres redis
```

### 5. Запуск бота

```bash
python main.py
```

## Деплой

### Render

1. Создайте новый Web Service на render.com
2. Подключите репозиторий
3. Добавьте переменные окружения из `.env.example`
4. Используйте команду запуска: `python main.py`

### Fly.io

```bash
flyctl launch
flyctl secrets set BOT_TOKEN=xxx DATABASE_URL=xxx GROQ_API_KEY=xxx
flyctl deploy
```

### Docker

```bash
docker build -t memory-bot .
docker run --env-file .env memory-bot
```

## Структура проекта

```
memory_bot/
├── main.py              # Точка входа
├── bot/
│   ├── handlers.py      # Обработчики сообщений
│   ├── book_handler.py  # Обработчики команды /book
│   ├── menu.py          # Меню и настройки
│   ├── export.py        # Простой экспорт PDF
│   └── i18n.py          # Локализация
├── book/
│   └── generator.py     # Генератор PDF-книг
├── templates/
│   └── book_template.html  # HTML шаблон книги
├── db/
│   ├── models.py        # SQLAlchemy модели
│   └── queries.py       # Функции для работы с БД
├── ai/
│   ├── transcriber.py   # Транскрипция аудио
│   ├── vision.py        # Описание изображений
│   └── embeddings.py    # Векторные эмбеддинги
├── docker-compose.yml   # PostgreSQL + Redis
└── requirements.txt     # Зависимости Python
```

## Технологический стек

- **Python 3.11+**
- **Aiogram 3.x** - Telegram бот фреймворк
- **SQLAlchemy + AsyncPG** - Асинхронная работа с БД
- **PostgreSQL + pgvector** - Хранение данных и векторный поиск
- **Groq API** - Транскрипция аудио и компьютерное зрение
- **WeasyPrint + Jinja2** - Генерация PDF книг
- **Redis** - Кэширование (опционально)
- **FastEmbed** - Векторные эмбеддинги для поиска

## База данных

### Таблицы

#### users
- `id` - Telegram user ID
- `username` - Имя пользователя
- `first_name` - Первое имя
- `language` - Язык интерфейса (ru/en)
- `created_at` - Дата регистрации

#### entries
- `id` - ID записи
- `user_id` - Ссылка на пользователя
- `type` - Тип (text/audio/photo/video)
- `text` - Текст записи
- `file_url` - Ссылка на файл (для audio/photo)
- `embedding` - Вектор для поиска (pgvector)
- `created_at` - Дата создания

## Лицензия

MIT License

## Контакты

Для вопросов и предложений обращайтесь к разработчику.
