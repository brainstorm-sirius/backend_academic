#!/bin/bash
# Не используем set -e, чтобы обрабатывать ошибки вручную
set -u  # Только проверка неопределенных переменных

echo "=== Academic Profile Backend Initialization ==="

# Функция для ожидания создания БД
wait_for_db() {
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if [ -f "/app/data/users.db" ]; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    return 1
}

# Создаем директорию для базы данных, если её нет
mkdir -p /app/data

# Убеждаемся, что users.db не является директорией (если это директория, удаляем)
if [ -d "/app/data/users.db" ]; then
    echo "⚠ Обнаружена директория users.db вместо файла. Удаляю..."
    rm -rf /app/data/users.db
fi

# Проверяем, существует ли база данных
if [ ! -f "/app/data/users.db" ]; then
    echo "База данных не найдена. Инициализация..."
    
    # Создаем БД через Python напрямую (быстрее и надежнее)
    echo "Создание базы данных..."
    if python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('База данных создана успешно!')
" 2>&1; then
        echo "✓ Команда создания БД выполнена успешно"
    else
        echo "⚠ Ошибка при создании БД через Python, попробуем альтернативный метод..."
    fi
    
    # Проверяем, что БД создана
    if [ -f "/app/data/users.db" ]; then
        echo "✓ База данных успешно создана!"
    else
        echo "⚠ Предупреждение: база данных не была создана. Попытка альтернативного метода..."
        # Альтернативный метод: запуск сервера для создания БД
        echo "Запуск временного сервера для создания БД..."
        uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        SERVER_PID=$!
        
        # Даем серверу время на запуск
        sleep 5
        
        # Обновляем функцию wait_for_db для нового пути
        local max_attempts=30
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if [ -f "/app/data/users.db" ]; then
                echo "✓ База данных создана через сервер!"
                break
            fi
            attempt=$((attempt + 1))
            sleep 1
        done
        
        if [ ! -f "/app/data/users.db" ]; then
            echo "⚠ База данных будет создана при первом запросе к серверу."
        fi
        
        echo "Остановка временного сервера..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
        sleep 2
    fi
    
    # Проверяем наличие CSV файлов и запускаем импорт
    # Проверяем в нескольких возможных местах
    CSV_AUTHORS=""
    CSV_INTERESTS=""
    
    # Проверяем CSV файлы в нескольких местах
    if [ -f "/app/csv_data/authors_expanded_with_ids.csv" ]; then
        CSV_AUTHORS="/app/csv_data/authors_expanded_with_ids.csv"
    elif [ -f "/app/authors_expanded_with_ids.csv" ]; then
        CSV_AUTHORS="/app/authors_expanded_with_ids.csv"
    fi
    
    if [ -f "/app/csv_data/authors_scientific_interests.csv" ]; then
        CSV_INTERESTS="/app/csv_data/authors_scientific_interests.csv"
    elif [ -f "/app/authors_scientific_interests.csv" ]; then
        CSV_INTERESTS="/app/authors_scientific_interests.csv"
    fi
    
    if [ -n "$CSV_AUTHORS" ] && [ -n "$CSV_INTERESTS" ]; then
        echo ""
        echo "Найдены CSV файлы. Запуск импорта данных..."
        echo "  - Authors: $CSV_AUTHORS"
        echo "  - Interests: $CSV_INTERESTS"
        
        # Копируем файлы в /app, если они находятся в другом месте
        if [ "$CSV_AUTHORS" != "/app/authors_expanded_with_ids.csv" ]; then
            echo "Копирование authors_expanded_with_ids.csv в /app..."
            cp "$CSV_AUTHORS" /app/authors_expanded_with_ids.csv
        fi
        if [ "$CSV_INTERESTS" != "/app/authors_scientific_interests.csv" ]; then
            echo "Копирование authors_scientific_interests.csv в /app..."
            cp "$CSV_INTERESTS" /app/authors_scientific_interests.csv
        fi
        
        echo "Запуск импорта данных..."
        echo "Это может занять некоторое время в зависимости от размера файлов..."
        if python import_csv.py 2>&1; then
            echo "✓ Импорт данных завершен!"
        else
            echo "⚠ Ошибка при импорте данных. Продолжаем запуск сервера..."
            echo "Сервер будет работать, но данные могут быть неполными."
        fi
    else
        echo ""
        echo "⚠ Предупреждение: CSV файлы не найдены. Импорт данных пропущен."
        if [ -z "$CSV_AUTHORS" ]; then
            echo "  - Отсутствует: authors_expanded_with_ids.csv"
        fi
        if [ -z "$CSV_INTERESTS" ]; then
            echo "  - Отсутствует: authors_scientific_interests.csv"
        fi
        echo ""
        echo "Для импорта данных поместите эти файлы в директорию backend_academic"
        echo "и перезапустите контейнер командой: docker compose restart backend"
    fi
else
    echo "✓ База данных уже существует. Пропуск инициализации."
    # Проверяем, что БД доступна
    if [ ! -f "/app/data/users.db" ]; then
        echo "⚠ Предупреждение: файл БД не найден, но директория существует. Пересоздаю..."
        rm -rf /app/data/users.db
        python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('База данных пересоздана!')
" 2>&1
    fi
fi

echo ""
echo "=== Запуск сервера ==="
echo "Backend будет доступен на http://0.0.0.0:8000"
echo "API документация: http://localhost:8000/docs"
echo ""

# Запускаем сервер (exec заменяет текущий процесс)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
