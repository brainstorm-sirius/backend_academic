# Инструкция по запуску через Docker

## Предварительные требования

- Docker версии 20.10 или выше
- Docker Compose версии 1.29 или выше

Проверка версий:
```bash
docker --version
docker-compose --version
```

## Быстрый старт

### 1. Подготовка переменных окружения (опционально)

Создайте файл `.env` в корне проекта (опционально, но рекомендуется):

```bash
SECRET_KEY=your-very-strong-secret-key-change-in-production
DATABASE_URL=sqlite:///./users.db
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Важно**: Если не создадите `.env`, будет использован слабый SECRET_KEY по умолчанию. В production это небезопасно!

### 2. Запуск приложения

```bash
# Собрать образ и запустить контейнер
docker-compose up -d

# Или с просмотром логов
docker-compose up
```

Приложение будет доступно по адресу: `http://localhost:8000`

### 3. Проверка работы

```bash
# Проверить статус контейнера
docker-compose ps

# Проверить логи
docker-compose logs -f

# Проверить health check
curl http://localhost:8000/health
```

## Управление контейнером

### Остановка

```bash
# Остановить контейнер
docker-compose stop

# Остановить и удалить контейнер
docker-compose down
```

### Перезапуск

```bash
# Перезапустить контейнер
docker-compose restart

# Пересобрать и перезапустить
docker-compose up -d --build
```

### Просмотр логов

```bash
# Все логи
docker-compose logs

# Логи в реальном времени
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100
```

## Работа с базой данных

### База данных сохраняется на хосте

База данных `users.db` монтируется как volume, поэтому данные сохраняются между перезапусками контейнера.

Расположение: `./users.db` в корне проекта

### Резервное копирование

```bash
# Создать резервную копию БД
cp users.db users.db.backup

# Восстановить из резервной копии
cp users.db.backup users.db
```

## Работа с моделью рекомендаций

Модель также монтируется как volume из папки `./model` на хосте.

Если нужно обновить модель:
1. Поместите новые файлы модели в папку `./model`
2. Перезапустите контейнер: `docker-compose restart`

## Переменные окружения

Можно переопределить переменные окружения через:

1. Файл `.env` (рекомендуется)
2. Прямо в `docker-compose.yml`
3. Через командную строку:

```bash
SECRET_KEY=my-secret docker-compose up
```

## Troubleshooting

### Проблема: Контейнер не запускается

```bash
# Проверить логи
docker-compose logs

# Проверить статус
docker-compose ps

# Пересобрать образ
docker-compose build --no-cache
docker-compose up
```

### Проблема: Порт 8000 уже занят

Измените порт в `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Внешний порт:внутренний порт
```

### Проблема: База данных не сохраняется

Убедитесь, что файл `users.db` существует и имеет правильные права:
```bash
touch users.db
chmod 666 users.db
```

### Проблема: Health check не проходит

Проверьте, что приложение запустилось:
```bash
docker-compose logs backend
curl http://localhost:8000/health
```

## Production deployment

### 1. Установите сильный SECRET_KEY

```bash
export SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Используйте PostgreSQL вместо SQLite

Измените `DATABASE_URL` в `docker-compose.yml`:
```yaml
environment:
  - DATABASE_URL=postgresql://user:password@postgres:5432/dbname
```

### 3. Настройте reverse proxy (nginx)

Пример конфигурации nginx:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Используйте HTTPS

Настройте SSL сертификат (Let's Encrypt) через nginx или используйте cloud provider.

## Полезные команды

```bash
# Войти в контейнер
docker-compose exec backend bash

# Выполнить команду в контейнере
docker-compose exec backend python -c "print('Hello')"

# Просмотреть использование ресурсов
docker stats academic_backend

# Очистить неиспользуемые образы
docker system prune -a
```

## Структура docker-compose.yml

- **build**: Сборка образа из Dockerfile
- **ports**: Проброс портов (8000:8000)
- **volumes**: Монтирование файлов с хоста
- **environment**: Переменные окружения
- **restart**: Автоматический перезапуск при падении
- **healthcheck**: Проверка здоровья контейнера

## Дополнительная информация

- Документация API: http://localhost:8000/docs
- Альтернативная документация: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

