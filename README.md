# Сервис регистрации и авторизации

FastAPI-приложение для регистрации пользователей, выдачи JWT-токенов и получения профиля. Поддерживаются поля:

`login`, `email`, `first_name`, `last_name`, `google_scholar_id`, `scopus_id`, `wos_id`, `rsci_id`, `orcid_id`, `password`.

## Стек
- FastAPI + Pydantic v2
- SQLAlchemy 2.x
- SQLite (по умолчанию) / любой SQLAlchemy-совместимый движок
- JWT (`python-jose`) и `passlib[bcrypt_sha256]` для хэширования
- Docker + Uvicorn

## Переменные окружения
| Переменная | Значение по умолчанию | Назначение |
|-----------|-----------------------|-----------|
| `DATABASE_URL` | `sqlite:///./users.db` | строка подключения SQLAlchemy |
| `SECRET_KEY` | `change-me` | ключ подписи JWT (замените в продакшене) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | TTL токена |

## Запуск локально
```bash
cd /Users/egorpetryaev/Documents/hack_oc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="your-secret"  # опционально
uvicorn app.main:app --reload
```
Приложение будет доступно по `http://127.0.0.1:8000`, swagger — `/docs`.

## Запуск в Docker
```bash
cd /Users/egorpetryaev/Documents/hack_oc
docker build -t user-auth .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=sqlite:///./users.db \
  user-auth
```

## Основные эндпоинты
### Регистрация
`POST /auth/register`
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "demo",
    "email": "user@example.com",
    "first_name": "Ivan",
    "last_name": "Ivanov",
    "password": "P@ssw0rd123",
    "google_scholar_id": "gs-123",
    "scopus_id": "sc-123",
    "wos_id": "wos-123",
    "rsci_id": "rsci-123",
    "orcid_id": "orcid-123"
  }'
```

### Логин
`POST /auth/login`
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{ "login_or_email": "demo", "password": "P@ssw0rd123" }'
```
Ответ содержит `access_token`. Используйте его как `Authorization: Bearer <token>`.

### Текущий пользователь
`GET /users/me`
```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer <token>"
```

## Работа с базой SQLite
```bash
source .venv/bin/activate           # если нужно
sqlite3 users.db
sqlite> .tables
sqlite> SELECT * FROM users;
sqlite> .quit
```

## Тестирование
- Проверить все сценарии через `http://localhost:8000/docs`.
- Для unit/e2e тестов можно подключить временную БД, указав `DATABASE_URL=sqlite:///./test.db`.

## Полезно знать
- Пароли хэшируются через `bcrypt_sha256`, длина не ограничена.
- Схемы валидируют email через `email-validator`.
- При смене БД обновите `DATABASE_URL`, миграции управляет сам SQLAlchemy (создание таблиц происходит автоматически при старте).

