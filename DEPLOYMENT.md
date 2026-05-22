# Инструкция по деплою Memory Bot

## Подготовка

### 1. Получение токенов и ключей

#### Telegram Bot Token
1. Откройте @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Сохраните полученный токен

#### Groq API Key
1. Перейдите на https://console.groq.com
2. Зарегистрируйтесь/войдите
3. Создайте API key в разделе "API Keys"
4. Сохраните ключ

### 2. Локальная настройка

```bash
# Клонирование репозитория
git clone <repository_url>
cd memory_bot

# Создание .env файла
cp .env.example .env

# Редактирование .env
nano .env  # или ваш любимый редактор
```

Заполните `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://memorybot:memorybot_password@localhost:5432/memorybot
GROQ_API_KEY=your_groq_api_key
```

## Деплой на Render

### Вариант 1: Web Service

1. Зарегистрируйтесь на https://render.com
2. Создайте новый **Web Service**
3. Подключите GitHub репозиторий
4. Настройки:
   - **Region**: Frankfurt (Europe)
   - **Branch**: main
   - **Root Directory**: (оставьте пустым)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

5. Добавьте переменные окружения:
   - `BOT_TOKEN`
   - `DATABASE_URL` (создайте PostgreSQL базу в Render)
   - `GROQ_API_KEY`

6. Нажмите **Create Web Service**

### Вариант 2: Docker

1. Создайте **Docker Service** на Render
2. Укажите Dockerfile из репозитория
3. Добавьте переменные окружения

## Деплой на Fly.io

```bash
# Установка flyctl
curl -L https://fly.io/install.sh | sh

# Авторизация
fly auth login

# Создание приложения
flyctl launch --name memory-bot

# Настройка секретов
flyctl secrets set \
    BOT_TOKEN=your_token \
    DATABASE_URL=postgres://user:pass@host:5432/db \
    GROQ_API_KEY=your_key

# Деплой
flyctl deploy
```

## Деплой с Docker Compose

### Для VPS (Ubuntu/Debian)

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh

# Копирование файлов на сервер
scp -r . user@server:/opt/memory_bot

# Настройка .env
ssh user@server
cd /opt/memory_bot
cp .env.example .env
nano .env  # заполните значения

# Запуск
docker-compose up -d postgres redis
docker-compose build
docker-compose up -d
```

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: memorybot
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secure_password}
      POSTGRES_DB: memorybot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U memorybot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

## Мониторинг и логи

### Render
- Логи доступны в дашборде
- Автоматический рестарт при падении

### Fly.io
```bash
flyctl logs --app memory-bot
flyctl status --app memory-bot
```

### Docker
```bash
docker-compose logs -f app
docker-compose ps
```

## Обновление

### Render
- Автоматически при push в main branch
- Или вручную через дашборд

### Fly.io
```bash
flyctl deploy
```

### Docker
```bash
git pull
docker-compose build
docker-compose up -d
```

## Безопасность

1. **Никогда не коммитьте .env файл**
2. Используйте secrets менеджеры для продакшена
3. Ограничьте доступ к базе данных
4. Регулярно обновляйте зависимости

## Troubleshooting

### Бот не запускается
```bash
# Проверьте логи
docker-compose logs app

# Проверьте переменные окружения
docker-compose exec app env | grep -E "BOT|DATABASE|GROQ"
```

### Ошибки подключения к БД
```bash
# Проверьте PostgreSQL
docker-compose exec postgres pg_isready -U memorybot

# Посмотрите логи PostgreSQL
docker-compose logs postgres
```

### Проблемы с памятью
```bash
# Очистка кэша pip
pip cache purge

# Удаление старых образов Docker
docker system prune -a
```

## Стоимость

### Render
- Web Service: $7/мес (базовый тариф)
- PostgreSQL: $7/мес (базовый тариф)
- Итого: ~$14/мес

### Fly.io
- App: ~$2/мес (shared CPU)
- PostgreSQL (сторонний): ~$7/мес
- Итого: ~$9/мес

### VPS + Docker
- VPS (Hetzner/DigitalOcean): ~$5-10/мес
- Итого: ~$5-10/мес

## Поддержка

Для вопросов создавайте issue в репозитории или обращайтесь к разработчику.
