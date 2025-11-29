# Academic Collaboration Platform Backend

FastAPI-приложение для регистрации учёных, поиска коллабораций и рекомендаций на основе научных интересов. Поддерживает работу с зарегистрированными пользователями и незарегистрированными авторами из научных баз данных.

## Основные возможности

- **Регистрация и авторизация** учёных с JWT токенами
- **Научные интересы** для пользователей
- **Публикации пользователей** - загрузка из Excel/CSV файлов
- **Поиск** по зарегистрированным пользователям и незарегистрированным авторам
- **Рекомендации** учёных на основе совпадения интересов (KNN алгоритм)
- **Профили авторов** с публикациями и аналитикой
- **Knowledge Graph** - визуализация связей между интересами и учёными
- **Импорт данных** из CSV файлов (авторы и их интересы)

## Стек технологий

- **Backend Framework**: FastAPI + Pydantic v2
- **База данных**: SQLAlchemy 2.x ORM + SQLite (по умолчанию)
- **Аутентификация**: JWT (`python-jose`) + `passlib[bcrypt_sha256]`
- **Рекомендации**: scikit-learn (KNN), pandas, numpy, scipy
- **Файлы**: openpyxl (для работы с Excel), pandas (для CSV)
- **Развёртывание**: Docker + Uvicorn
- **CORS**: Настроен для работы с frontend

## Архитектура системы

### Общая структура

Приложение построено по принципу многослойной архитектуры:

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│         (app/main.py)                   │
├─────────────────────────────────────────┤
│  API Layer (Endpoints)                  │
│  - Authentication                       │
│  - User Management                      │
│  - Search & Recommendations             │
│  - Knowledge Graph                      │
├─────────────────────────────────────────┤
│  Business Logic Layer                   │
│  - Auth Service (app/auth.py)           │
│  - Recommender Service (app/recommender)│
├─────────────────────────────────────────┤
│  Data Access Layer                      │
│  - Models (app/models.py)               │
│  - Database (app/database.py)           │
├─────────────────────────────────────────┤
│  Data Validation Layer                   │
│  - Schemas (app/schemas.py)             │
└─────────────────────────────────────────┘
```

### Компоненты системы

1. **API Layer** (`app/main.py`)
   - Обработка HTTP запросов
   - Валидация входных данных через Pydantic
   - Маршрутизация запросов к соответствующим сервисам

2. **Authentication Service** (`app/auth.py`)
   - Хеширование паролей (bcrypt)
   - Генерация и валидация JWT токенов
   - Dependency Injection для получения текущего пользователя

3. **Recommender Service** (`app/recommender.py`)
   - Загрузка обученной модели (KNN)
   - Векторизация интересов (TF-IDF)
   - Поиск похожих учёных

4. **Database Layer** (`app/database.py`, `app/models.py`)
   - Настройка подключения к БД
   - ORM модели для работы с данными
   - Автоматическое создание таблиц

5. **Validation Layer** (`app/schemas.py`)
   - Pydantic схемы для валидации входных данных
   - Схемы для сериализации ответов

## Структура базы данных

### Диаграмма связей

```
┌─────────────┐
│    users    │
│─────────────│
│ id (PK)     │
│ login       │◄──────────┐
│ email       │           │
│ interests_  │           │
│   list      │           │
└─────────────┘           │
      │                   │
      │ 1:N               │
      │                   │
      ▼                   │
┌──────────────────┐      │
│ user_publications│      │
│──────────────────│      │
│ id (PK)          │      │
│ user_id (FK)     │──────┘
│ title            │
│ coauthors        │
│ citations        │
│ journal          │
│ publication_year │
└──────────────────┘

┌─────────────┐
│   authors   │
│─────────────│
│ id (PK)     │
│ author_id   │──┐
│ author_name │  │
│ title       │  │
│ journal     │  │
└─────────────┘  │
                 │
                 │ (логическая связь через author_id)
                 │
                 ▼
┌──────────────────┐
│ author_interests │
│──────────────────│
│ id (PK)          │
│ author_id (UK)   │◄──┘
│ author_name      │
│ interests_list   │
│ keywords_list    │
│ articles_count   │
│ interests_count  │
│ main_interest    │
└──────────────────┘
```

### Детальное описание таблиц

#### Таблица `users` (зарегистрированные пользователи)

**Назначение**: Хранит данные зарегистрированных учёных

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор пользователя
- `login` (String(255), UNIQUE, NOT NULL, INDEX) - Логин пользователя
- `email` (String(255), UNIQUE, NOT NULL, INDEX) - Email адрес
- `first_name` (String(255), NOT NULL) - Имя
- `last_name` (String(255), NOT NULL) - Фамилия
- `google_scholar_id` (String(255), NULL) - ID в Google Scholar
- `scopus_id` (String(255), NULL) - ID в Scopus
- `wos_id` (String(255), NULL) - ID в Web of Science
- `rsci_id` (String(255), NULL) - ID в РИНЦ
- `orcid_id` (String(255), NULL) - ID в ORCID
- `interests_list` (Text, NULL) - Список научных интересов через запятую
- `password_hash` (String(255), NOT NULL) - Хеш пароля (bcrypt)

**Связи**:
- Один-ко-многим с `user_publications` (cascade delete)

**Индексы**: `login`, `email`

#### Таблица `user_publications` (публикации пользователей)

**Назначение**: Хранит публикации зарегистрированных пользователей

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор публикации
- `user_id` (Integer, FK → users.id, NOT NULL, INDEX) - Ссылка на пользователя
- `title` (Text, NOT NULL) - Название статьи
- `coauthors` (Text, NULL) - Соавторы
- `citations` (String(50), NULL) - Количество цитирований
- `journal` (String(500), NULL) - Название журнала
- `publication_year` (String(10), NULL) - Год публикации
- `author_name` (String(500), NULL) - Имя автора

**Связи**:
- Многие-к-одному с `users` (ondelete="CASCADE")

**Индексы**: `user_id`

#### Таблица `authors` (незарегистрированные авторы)

**Назначение**: Хранит информацию о незарегистрированных авторах и их публикациях

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор записи
- `pmid` (String(50), INDEX) - PubMed ID
- `title` (Text, NULL) - Название статьи
- `authors_original` (Text, NULL) - Оригинальный список авторов
- `citation` (Text, NULL) - Полная цитата
- `journal_book` (String(500), NULL) - Журнал или книга
- `publication_year` (String(10), NULL) - Год публикации
- `create_date` (String(50), NULL) - Дата создания записи
- `pmcid` (String(50), NULL) - PubMed Central ID
- `nihms_id` (String(50), NULL) - NIHMS ID
- `doi` (String(255), NULL) - DOI статьи
- `author_name` (String(500), INDEX) - Имя автора (для поиска)
- `author_id` (String(100), INDEX) - Уникальный ID автора

**Связи**:
- Логическая связь с `author_interests` через `author_id` (не FK, т.к. разные типы)

**Индексы**: `pmid`, `author_name`, `author_id`

#### Таблица `author_interests` (научные интересы авторов)

**Назначение**: Хранит научные интересы незарегистрированных авторов

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `author_id` (String(100), UNIQUE, NOT NULL, INDEX) - Уникальный ID автора
- `author_name` (String(500), INDEX) - Имя автора
- `interests_list` (Text, NULL) - Список интересов через запятую
- `keywords_list` (Text, NULL) - Список ключевых слов
- `interests_count` (Integer, NULL) - Количество интересов
- `articles_count` (Integer, NULL) - Количество статей
- `main_interest` (String(255), NULL) - Основной интерес
- `cluster` (Integer, NULL) - Кластер для группировки

**Связи**:
- Логическая связь с `authors` через `author_id`

**Индексы**: `author_id`, `author_name`

### Взаимосвязи таблиц

1. **users ↔ user_publications**: 
   - Связь: Один-ко-многим (один пользователь - много публикаций)
   - Тип: Foreign Key с каскадным удалением
   - При удалении пользователя удаляются все его публикации

2. **authors ↔ author_interests**:
   - Связь: Один-к-одному (один author_id - одна запись интересов)
   - Тип: Логическая связь через `author_id` (не FK, т.к. разные типы данных)
   - Связь устанавливается по совпадению `authors.author_id` = `author_interests.author_id`

3. **Объединение данных**:
   - Зарегистрированные пользователи (`users`) и незарегистрированные авторы (`authors`) объединяются в поиске и рекомендациях
   - Связь через общие научные интересы (`interests_list`)

## Переменные окружения

| Переменная | Значение по умолчанию | Назначение |
|-----------|-----------------------|-----------|
| `DATABASE_URL` | `sqlite:///./users.db` | строка подключения SQLAlchemy |
| `SECRET_KEY` | `change-me` | ключ подписи JWT (замените в продакшене) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | TTL токена в минутах |

## Установка и запуск

### Локальный запуск

```bash
# Клонируйте репозиторий
cd backend_academic

# Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt

# (Опционально) Установите переменные окружения
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite:///./users.db"

# Запустите приложение
uvicorn app.main:app --reload
```

Приложение будет доступно по `http://127.0.0.1:8000`
- API документация (Swagger): `http://127.0.0.1:8000/docs`
- Альтернативная документация (ReDoc): `http://127.0.0.1:8000/redoc`

### Запуск в Docker

#### Использование docker-compose (рекомендуется)

```bash
# Запустить приложение
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановить приложение
docker-compose down
```

#### Использование Docker напрямую

```bash
# Соберите образ
docker build -t academic-backend .

# Запустите контейнер
docker run --rm -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=sqlite:///./users.db \
  -v $(pwd)/users.db:/app/users.db \
  -v $(pwd)/model:/app/model \
  academic-backend
```

## Импорт данных из CSV

Для импорта данных о незарегистрированных авторах:

```bash
# Импорт авторов и их публикаций
python import_csv.py
```

Скрипт импортирует:
- `authors_expanded_with_ids.csv` → таблица `authors`
- `authors_scientific_interests.csv` → таблица `author_interests`

**Важно**: 
- CSV файлы **не включены в git** из-за их размера (~127MB)
- Получите CSV файлы у команды или создайте их самостоятельно
- Убедитесь, что CSV файлы находятся в корне проекта перед импортом

## API Endpoints

### Аутентификация

#### Регистрация
`POST /auth/register`

Создаёт нового пользователя в системе.

**Параметры**:
- `login` (string, min 3) - Уникальный логин
- `email` (email) - Email адрес
- `first_name` (string) - Имя
- `last_name` (string) - Фамилия
- `password` (string, min 8) - Пароль
- `google_scholar_id`, `scopus_id`, `wos_id`, `rsci_id`, `orcid_id` (optional) - ID в научных базах

**Пример**:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "scientist123",
    "email": "scientist@example.com",
    "first_name": "Иван",
    "last_name": "Иванов",
    "password": "SecurePass123",
    "orcid_id": "0000-0000-0000-0000"
  }'
```

#### Вход
`POST /auth/login`

Возвращает JWT токен для авторизованных запросов.

**Параметры**:
- `login_or_email` (string) - Логин или email
- `password` (string) - Пароль

**Ответ**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Пользователи

#### Получить текущего пользователя
`GET /users/me`

Требует авторизации. Возвращает данные текущего пользователя.

**Заголовки**: `Authorization: Bearer <token>`

#### Обновить научные интересы
`PUT /users/interests`

Обновляет список научных интересов пользователя.

**Параметры**:
- `login` (string) - Логин пользователя
- `interests_list` (array of strings) - Список интересов

#### Загрузить публикации из файла
`POST /users/{user_id}/publications/upload`

Загружает публикации из Excel или CSV файла.

**Параметры**:
- `user_id` (path) - ID пользователя
- `file` (multipart/form-data) - Файл с публикациями

**Поддерживаемые форматы**: CSV (.csv), Excel (.xlsx, .xls)

**Поддерживаемые названия столбцов**:
- Название статьи (обязательно): "Название статьи", "Title", "ArticleTitle"
- Соавторы: "Соавторы", "Coauthors", "Co-authors"
- Цитирование: "Цитирование", "Citations"
- Журнал: "Журнал", "Journal", "Source"
- Год публикации: "Год публикации", "Year", "Year of Publication"
- Имя автора: "Имя автора", "Author Name", "Author"

**Публичный endpoint** - не требует авторизации

#### Получить публикации пользователя
`GET /users/{user_id}/publications`

Возвращает все публикации указанного пользователя.

**Публичный endpoint** - не требует авторизации

#### Удалить публикацию
`DELETE /users/{user_id}/publications/{publication_id}`

Удаляет публикацию пользователя.

**Публичный endpoint** - не требует авторизации

### Поиск

#### Объединённый поиск
`GET /search?query={query}&limit={limit}`

Ищет по зарегистрированным пользователям (по username) и незарегистрированным авторам (по имени).

**Параметры**:
- `query` (string, min 2) - Поисковый запрос
- `limit` (int, 1-100, default 10) - Максимальное количество результатов

**Ответ включает**:
- `registered_users` - Зарегистрированные пользователи
- `unregistered_authors` - Незарегистрированные авторы
- `author_interests` - Научные интересы найденных авторов

#### Поиск только пользователей
`GET /search/users?username={username}&limit={limit}`

#### Поиск только авторов
`GET /search/authors?name={name}&limit={limit}`

### Авторы

#### Получить научные интересы автора
`GET /authors/{author_id}/interests`

Возвращает научные интересы автора по его `author_id`.

#### Получить полный профиль автора
`GET /authors/{author_id}/profile`

Возвращает полный профиль автора с публикациями и аналитикой.

**Ответ включает**:
- Информацию об учёном (имя, ORCID, метрики)
- Аналитику (индекс, среднее, производительность)
- Распределение тем (topicDistribution)
- Список публикаций

### Рекомендации

#### Получить рекомендации учёных по интересам
`POST /recommend`

Использует обученную модель (KNN) для поиска похожих учёных.

**Параметры**:
- `interests` (array of strings) - Список научных интересов
- `publications` (array of strings, optional) - Список публикаций для анализа
- `num_recommendations` (int, 1-100, default 10) - Количество рекомендаций

**Алгоритм**:
1. Создаёт профиль из интересов и публикаций
2. Векторизует через TF-IDF
3. Находит ближайших соседей через KNN
4. Ранжирует по комбинированному скору:
   - Similarity (60%) - похожесть интересов
   - Productivity (25%) - количество статей
   - Diversity (15%) - разнообразие интересов

**Ответ**:
```json
{
  "recommendations": [
    {
      "author_id": "abc123",
      "author_name": "John Doe",
      "total_score": 0.85,
      "similarity_score": 0.75,
      "productivity_score": 0.9,
      "diversity_score": 0.8,
      "articles_count": 50,
      "interests_count": 5,
      "main_interest": "AI"
    }
  ],
  "processing_time": 0.123
}
```

### Knowledge Graph

#### Получить данные для knowledge graph
`GET /knowledge-graph`

**Требует авторизации**: Да (Bearer token)

Возвращает все уникальные интересы и топ-100 наиболее релевантных учёных для текущего пользователя на основе их научных интересов. Учёные сортируются по степени совпадения интересов с текущим пользователем.

**Ответ**:
```json
{
  "interests": [
    {
      "id": 1,
      "name": "Machine Learning",
      "scientist_count": 15
    }
  ],
  "scientists": [
    {
      "id": 1,
      "name": "Иван Иванов",
      "username": "scientist123",
      "interests": [1, 2]
    }
  ]
}
```

**Логика работы**:
1. Собирает все уникальные интересы из `users.interests_list` и `author_interests.interests_list`
2. Подсчитывает количество уникальных учёных для каждого интереса
3. Присваивает каждому интересу уникальный ID (начиная с 1)
4. Выбирает 100 случайных учёных (зарегистрированных и незарегистрированных)
5. Связывает учёных с интересами через ID

### Система

#### Проверка здоровья приложения
`GET /health`

Возвращает статус приложения и модели.

**Ответ**:
```json
{
  "status": "healthy",
  "authors_count": 194850,
  "model_loaded": true
}
```

## Модель рекомендаций

Приложение использует обученную модель для рекомендаций учёных:

**Алгоритм**: K-Nearest Neighbors (KNN) с косинусным расстоянием
**Векторизация**: TF-IDF (Term Frequency-Inverse Document Frequency)
**Метрики ранжирования**:
- Similarity (60%) - похожесть научных интересов
- Productivity (25%) - количество публикаций
- Diversity (15%) - разнообразие интересов

**Структура модели**:
- `authors_data.pkl` - Данные об авторах (DataFrame)
- `vectorizer.pkl` - TF-IDF векторизатор
- `author_vectors.npz` - Векторизованные профили авторов
- `knn_model.pkl` - Обученная KNN модель

Модель загружается автоматически при старте приложения из папки `model/`.

**Важно**: 
- Папка `model/` **не включена в git** из-за размера файлов (~83MB)
- Получите готовую модель у команды или обучите самостоятельно

Для обучения новой модели используйте `train_model.py`:
```bash
# Убедитесь, что файл authors_scientific_interests.csv находится в корне проекта
python train_model.py
```

## CORS

Приложение настроено для работы с frontend на следующих портах:
- `http://localhost:5173` (Vite)
- `http://localhost:3000` (React)
- `http://localhost:8080` (Vue)
- `http://localhost` (общий)

Для добавления других доменов отредактируйте список `origins` в `app/main.py`.

## Работа с базой данных

### SQLite

```bash
# Подключение к БД
sqlite3 users.db

# Просмотр таблиц
.tables

# Просмотр пользователей
SELECT * FROM users;

# Просмотр публикаций пользователя
SELECT * FROM user_publications WHERE user_id = 1;

# Просмотр авторов
SELECT * FROM authors LIMIT 10;

# Просмотр интересов авторов
SELECT * FROM author_interests LIMIT 10;

# Выход
.quit
```

### Автоматическое создание таблиц

Все таблицы создаются автоматически при первом запуске приложения через `models.Base.metadata.create_all(bind=engine)` в `app/main.py`.

## Тестирование

- **Swagger UI**: `http://localhost:8000/docs` - интерактивная документация API
- **ReDoc**: `http://localhost:8000/redoc` - альтернативная документация

Для тестирования используйте временную БД:
```bash
export DATABASE_URL="sqlite:///./test.db"
```

## Полезная информация

- Пароли хэшируются через `bcrypt_sha256`
- Email валидируется через `email-validator`
- Таблицы создаются автоматически при первом запуске
- Модель рекомендаций должна находиться в папке `model/` в корне проекта
- При отсутствии модели приложение запустится, но рекомендации не будут работать
- Публикации пользователей можно загружать из CSV или Excel файлов
- Поддерживаются различные варианты названий столбцов (русский/английский)

## Безопасность

- **Важно**: Замените `SECRET_KEY` на случайную строку в продакшене
- Используйте HTTPS в продакшене
- Настройте CORS для конкретных доменов вместо широкого доступа в продакшене
- Endpoints для публикаций пользователей публичные (без авторизации) - рассмотрите добавление авторизации в продакшене
- Регулярно обновляйте зависимости

## Структура проекта

```
backend_academic/
├── app/                    # Основной код приложения
│   ├── __init__.py
│   ├── main.py            # FastAPI приложение и endpoints
│   ├── models.py          # SQLAlchemy модели (таблицы БД)
│   ├── schemas.py         # Pydantic схемы (валидация данных)
│   ├── auth.py           # Аутентификация и JWT
│   ├── database.py       # Настройка подключения к БД
│   └── recommender.py    # Сервис рекомендаций (KNN)
├── model/                 # Обученная модель (не в git)
│   ├── authors_data.pkl
│   ├── vectorizer.pkl
│   ├── author_vectors.npz
│   └── knn_model.pkl
├── import_csv.py         # Скрипт импорта CSV данных
├── train_model.py        # Скрипт обучения модели
├── requirements.txt      # Зависимости Python
├── Dockerfile           # Docker конфигурация
└── README.md           # Документация
```

## Лицензия

[Укажите вашу лицензию]

## Авторы

[Укажите авторов проекта]
