# Базовый образ
FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Создание директории приложения
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем проект
COPY . .

# Установка пути к виртуальному окружению
ENV PATH="/opt/venv/bin:$PATH"

# Команда запуска
CMD bash -c "\
    python backend/manage.py makemigrations && \
    python backend/manage.py migrate && \
    python backend/manage.py runserver 0.0.0.0:8000"
