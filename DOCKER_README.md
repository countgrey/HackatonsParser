# Docker Compose для HackatonsParser

Эта версия Docker Compose разделяет систему на отдельные контейнеры для лучшей масштабируемости и управления.

## Архитектура

- **ollama** - Контейнер с Ollama и моделью Mistral для LLM-обработки
- **ollama-init** - Одноразовый контейнер для инициализации модели
- **parser** - Контейнер парсера с доступом к Ollama
- **bot** - Контейнер Telegram бота с доступом к базе данных

## Запуск

### 1. Подготовка файлов

```bash
# Скопируйте новые файлы конфигурации
cp .env.new .env
cp docker-compose.new.yml docker-compose.yml
```

### 2. Запуск всей системы

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f bot
docker-compose logs -f parser
```

### 3. Поэтапный запуск (рекомендуется)

```bash
# Шаг 1: Запуск Ollama
docker-compose up -d ollama

# Шаг 2: Инициализация модели (выполняется один раз)
docker-compose up ollama-init

# Шаг 3: Запуск парсера
docker-compose up -d parser

# Шаг 4: Запуск бота
docker-compose up -d bot
```

## Управление сервисами

### Остановка системы
```bash
docker-compose down
```

### Перезапуск конкретного сервиса
```bash
# Перезапуск бота
docker-compose restart bot

# Перезапуск парсера
docker-compose restart parser

# Перезапуск Ollama
docker-compose restart ollama
```

### Обновление образов
```bash
# Пересборка образов
docker-compose build --no-cache

# Перезапуск с новыми образами
docker-compose up -d --force-recreate
```

## Проверка состояния

### Статус всех сервисов
```bash
docker-compose ps
```

### Проверка доступности Ollama
```bash
curl http://localhost:11434/api/tags
```

### Проверка логов бота
```bash
docker-compose logs bot | tail -20
```

### Проверка логов парсера
```bash
docker-compose logs parser | tail -20
```

## Первичная настройка

### 1. Проверка модели Ollama
```bash
docker-compose exec ollama ollama list
```

Должна быть видна модель `mistral:7b`

### 2. Проверка базы данных
```bash
docker-compose exec bot python -c "
import sqlite3
conn = sqlite3.connect('/app/smart_filtered.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM smart_events')
print(f'Событий в базе: {cursor.fetchone()[0]}')
conn.close()
"
```

### 3. Проверка Telegram бота
Отправьте команду `/start` вашему боту в Telegram.

## Отладка

### Вход в контейнер бота
```bash
docker-compose exec bot bash
```

### Вход в контейнер парсера
```bash
docker-compose exec parser bash
```

### Вход в контейнер Ollama
```bash
docker-compose exec ollama bash
```

### Просмотр файловой системы
```bash
# Просмотр логов
docker-compose exec bot ls -la /app/logs/

# Просмотр базы данных
docker-compose exec bot ls -la /app/*.db
```

## Конфигурация

### Переменные окружения (.env)
- `BOT_TOKEN` - Токен Telegram бота
- `OLLAMA_URL` - URL сервиса Ollama (по умолчанию http://ollama:11434)
- `MODEL_NAME` - Название модели LLM (по умолчанию mistral)
- `DATABASE_NAME` - Имя файла базы данных для бота
- `ITEMS_PER_PAGE` - Количество элементов на странице в боте
- `LOG_LEVEL` - Уровень логирования

### Настройка расписания парсера
Измените в файле `run_parser.py` или добавьте переменную окружения:
```yaml
parser:
  environment:
    - PARSER_SCHEDULE=03:00  # Ежедневно в 03:00
```

## Безопасность

- Все сервисы работают в изолированной сети `hackatons_network`
- Ollama доступен только внутри Docker сети
- База данных монтируется как том Docker для сохранности данных
- Переменные окружения загружаются из .env файла

## Производительность

- Парсер работает по расписанию и не нагружает систему постоянно
- Бот работает постоянно и готов к обработке запросов
- Ollama кэширует модель в томе для быстрого доступа
- База данных оптимизирована для быстрых запросов