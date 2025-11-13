# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы с зависимостями
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p logs

# Создаем файл .env если его нет (можно переопределить при запуске)
RUN touch .env

# Открываем порт (если нужно для веб-хуков)
EXPOSE 8443

# Запускаем планировщик
CMD ["python", "main.py"]
