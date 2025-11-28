# Подробное объяснение бэкенда

## 🎯 Общая архитектура

Ваш бэкенд использует **FastAPI** - современный фреймворк для создания API на Python.

### Структура файлов:

```
app/
├── database.py  → Подключение к БД
├── models.py    → Структура таблиц (SQLAlchemy)
├── schemas.py   → Валидация данных (Pydantic)
├── auth.py      → Аутентификация и авторизация
└── main.py      → API endpoints (роуты)
```

---

## 📁 1. database.py - Подключение к базе данных

### Что делает:
Создаёт "мост" между вашим кодом и базой данных.

### Ключевые понятия:

**Engine (движок)** - это подключение к БД. Как ключ от двери.
```python
engine = create_engine(DATABASE_URL)
```

**SessionLocal** - фабрика для создания сессий.
- Сессия = "разговор" с БД
- Каждый запрос получает свою сессию
- После использования сессия закрывается

**Base** - базовый класс для всех моделей (таблиц).
- Все ваши таблицы наследуются от `Base`
- SQLAlchemy автоматически понимает структуру таблиц

### Как использовать:
```python
# В других файлах:
from .database import SessionLocal, Base

# Создать сессию:
db = SessionLocal()
# ... работа с БД ...
db.close()
```

---

## 📁 2. models.py - Структура таблиц

### Что делает:
Описывает структуру таблицы `users` в базе данных.

### Ключевые понятия:

**Column** - колонка в таблице:
- `Integer` - целое число
- `String(255)` - строка до 255 символов

**Параметры Column:**
- `primary_key=True` - уникальный идентификатор (id)
- `unique=True` - значение должно быть уникальным
- `nullable=False` - поле обязательно
- `index=True` - создаётся индекс для быстрого поиска

### Пример:
```python
login = Column(String(255), unique=True, nullable=False, index=True)
# Это означает:
# - строка до 255 символов
# - уникальное значение
# - обязательно к заполнению
# - с индексом для быстрого поиска
```

### Как добавить новое поле:
```python
class User(Base):
    # ... существующие поля ...
    new_field = Column(String(255))  # Новое поле
```

---

## 📁 3. schemas.py - Валидация данных

### Что делает:
Проверяет данные, которые приходят от пользователя и которые вы отправляете обратно.

### Зачем нужны схемы:
1. **Валидация** - проверяют формат данных ДО записи в БД
2. **Безопасность** - не возвращают пароль в ответах
3. **Документация** - FastAPI автоматически создаёт документацию API

### Типы схем:

**UserBase** - базовые поля (общие для создания и ответа):
```python
class UserBase(BaseModel):
    login: str = Field(..., min_length=3, max_length=255)
    # ... означает обязательное поле
```

**UserCreate** - для регистрации (UserBase + password):
```python
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
```

**UserResponse** - что возвращаем пользователю (UserBase + id, БЕЗ password):
```python
class UserResponse(UserBase):
    id: int
```

**UserLogin** - для входа:
```python
class UserLogin(BaseModel):
    login_or_email: str  # Можно ввести login или email
    password: str
```

**Token** - ответ при логине:
```python
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

### Field() параметры:
- `Field(...)` - обязательное поле
- `Field(..., min_length=8)` - минимум 8 символов
- `Optional[str] = None` - необязательное поле

---

## 📁 4. auth.py - Аутентификация и авторизация

### Что делает:
Управляет безопасностью: хеширование паролей, создание токенов, проверка прав доступа.

### Ключевые компоненты:

**pwd_context** - для хеширования паролей:
```python
pwd_context = CryptContext(schemes=["bcrypt_sha256"])
# bcrypt - безопасный алгоритм хеширования
```

**oauth2_scheme** - схема OAuth2 для токенов:
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Говорит FastAPI, где искать токен (в заголовке Authorization)
```

### Функции:

#### 1. `get_db()` - Dependency Injection для сессии БД
```python
def get_db():
    db = SessionLocal()  # Создаём сессию
    try:
        yield db  # Отдаём сессию функции
    finally:
        db.close()  # Закрываем после использования
```

**Зачем `yield`?**
- `yield` создаёт генератор
- FastAPI автоматически вызывает `finally` после завершения функции
- Гарантирует закрытие сессии даже при ошибке

#### 2. `get_password_hash()` - хеширует пароль
```python
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
# "mypassword123" → "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5..."
```

**Зачем хешировать?**
- Пароли НЕ хранятся в открытом виде
- Даже если БД взломают, пароли не узнают

#### 3. `verify_password()` - проверяет пароль
```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
# Сравнивает введённый пароль с хешем из БД
```

#### 4. `create_access_token()` - создаёт JWT токен
```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Что такое JWT токен?**
- JSON Web Token - закодированная строка
- Содержит: user_id, время истечения
- Подписан SECRET_KEY (только сервер знает ключ)
- Клиент отправляет токен в заголовке: `Authorization: Bearer <token>`

**Пример токена:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

#### 5. `get_current_user()` - получает текущего пользователя
```python
def get_current_user(
    token: str = Depends(oauth2_scheme),  # Автоматически извлекает токен
    db: Session = Depends(get_db),        # Автоматически создаёт сессию
) -> models.User:
    # 1. Декодирует токен
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    
    # 2. Находит пользователя в БД
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # 3. Возвращает объект User
    return user
```

**Как работает `Depends()`?**
- FastAPI автоматически вызывает функцию перед вашей
- Результат передаётся как параметр
- Это называется **Dependency Injection**

---

## 📁 5. main.py - API Endpoints

### Что делает:
Определяет маршруты (endpoints) вашего API.

### Ключевые понятия:

**FastAPI приложение:**
```python
app = FastAPI(title="User Auth Service")
```

**Декораторы:**
- `@app.post("/auth/register")` - POST запрос
- `@app.get("/users/me")` - GET запрос
- `@app.put(...)` - PUT запрос
- `@app.delete(...)` - DELETE запрос

**Параметры декоратора:**
- `response_model=schemas.UserResponse` - формат ответа
- `status_code=201` - код ответа

### Эндпоинты:

#### 1. POST `/auth/register` - Регистрация

**Что делает:**
1. Проверяет, не занят ли login
2. Проверяет, не занят ли email
3. Хеширует пароль
4. Создаёт пользователя в БД
5. Возвращает данные пользователя (без пароля)

**Код:**
```python
@app.post("/auth/register", response_model=schemas.UserResponse, status_code=201)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # Проверка login
    login_exists = db.query(models.User).filter(models.User.login == payload.login).first()
    if login_exists:
        raise HTTPException(status_code=400, detail="Login already taken")
    
    # Проверка email
    email_exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Создание пользователя
    user = models.User(
        login=payload.login,
        email=payload.email,
        # ... остальные поля ...
        password_hash=get_password_hash(payload.password),  # Хешируем пароль!
    )
    
    # Сохранение в БД
    db.add(user)      # Добавляем в сессию
    db.commit()       # Сохраняем в БД
    db.refresh(user)  # Обновляем объект (получаем id)
    
    return user  # FastAPI автоматически конвертирует в UserResponse (без password)
```

**Работа с БД:**
- `db.query(models.User)` - запрос к таблице users
- `.filter(...)` - условие поиска
- `.first()` - получить первый результат (или None)
- `db.add(user)` - добавить в сессию
- `db.commit()` - сохранить изменения
- `db.refresh(user)` - обновить объект из БД

#### 2. POST `/auth/login` - Вход

**Что делает:**
1. Ищет пользователя по login ИЛИ email
2. Проверяет пароль
3. Создаёт токен
4. Возвращает токен

**Код:**
```python
@app.post("/auth/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    # Поиск пользователя
    user = db.query(models.User).filter(
        (models.User.login == payload.login_or_email)
        | (models.User.email == payload.login_or_email)  # | = ИЛИ
    ).first()
    
    # Проверка пароля
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Создание токена
    token = create_access_token({"sub": str(user.id)})
    
    return schemas.Token(access_token=token)
```

**Как использовать токен:**
Клиент отправляет запросы с заголовком:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 3. GET `/users/me` - Получить текущего пользователя

**Что делает:**
Возвращает данные текущего авторизованного пользователя.

**Код:**
```python
@app.get("/users/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user
```

**Как работает:**
1. `Depends(get_current_user)` автоматически:
   - Извлекает токен из заголовка `Authorization`
   - Проверяет токен
   - Находит пользователя в БД
   - Передаёт объект User в функцию
2. Если токен невалидный → ошибка 401
3. Функция просто возвращает пользователя

---

## 🔄 Как всё работает вместе

### Пример: Регистрация пользователя

1. **Клиент отправляет запрос:**
```json
POST /auth/register
{
  "login": "scientist123",
  "email": "scientist@example.com",
  "password": "securepass123",
  "first_name": "Иван",
  "last_name": "Иванов",
  "google_scholar_id": "abc123",
  "orcid_id": "0000-0000-0000-0000"
}
```

2. **FastAPI валидирует данные:**
   - Использует `schemas.UserCreate`
   - Проверяет: длина login ≥ 3, email валидный, password ≥ 8 символов

3. **Функция `register_user()`:**
   - Проверяет уникальность login и email
   - Хеширует пароль через `get_password_hash()`
   - Создаёт объект `models.User`
   - Сохраняет в БД через `db.add()` и `db.commit()`

4. **Ответ клиенту:**
```json
{
  "id": 1,
  "login": "scientist123",
  "email": "scientist@example.com",
  "first_name": "Иван",
  "last_name": "Иванов",
  "google_scholar_id": "abc123",
  "orcid_id": "0000-0000-0000-0000"
  // password НЕ возвращается!
}
```

### Пример: Вход и получение данных

1. **Клиент логинится:**
```json
POST /auth/login
{
  "login_or_email": "scientist123",
  "password": "securepass123"
}
```

2. **Сервер проверяет и возвращает токен:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. **Клиент запрашивает свои данные:**
```
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

4. **Сервер:**
   - `get_current_user()` извлекает токен
   - Декодирует токен → получает user_id
   - Находит пользователя в БД
   - Возвращает данные пользователя

---

## 🛠 Как добавлять новые функции

### Пример 1: Добавить новое поле в модель

1. **models.py:**
```python
class User(Base):
    # ... существующие поля ...
    phone = Column(String(20))  # Новое поле
```

2. **schemas.py:**
```python
class UserBase(BaseModel):
    # ... существующие поля ...
    phone: Optional[str] = None
```

3. **main.py (в register_user):**
```python
user = models.User(
    # ... существующие поля ...
    phone=payload.phone,
)
```

### Пример 2: Добавить новый endpoint

```python
@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Пример 3: Защитить endpoint (только для авторизованных)

```python
@app.delete("/users/me")
def delete_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted"}
```

---

## 📚 Полезные команды

### Запуск сервера:
```bash
uvicorn app.main:app --reload
```

### Документация API:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Тестирование API:
```bash
# Регистрация
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"login":"test","email":"test@test.com","password":"test1234","first_name":"Test","last_name":"User"}'

# Логин
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login_or_email":"test","password":"test1234"}'

# Получить данные (замените TOKEN)
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer TOKEN"
```

---

## 🎓 Ключевые концепции для понимания

### 1. Dependency Injection (DI)
FastAPI автоматически вызывает функции с `Depends()` и передаёт результат как параметр.

### 2. ORM (Object-Relational Mapping)
SQLAlchemy позволяет работать с БД через Python объекты, а не SQL запросы.

### 3. Pydantic Models
Автоматическая валидация данных и конвертация типов.

### 4. JWT Tokens
Безопасный способ передачи информации о пользователе без хранения состояния на сервере.

### 5. Password Hashing
Пароли никогда не хранятся в открытом виде, только хеши.

---

## ✅ Чеклист для самостоятельной работы

- [ ] Понимаю, как работает `Depends()` и Dependency Injection
- [ ] Знаю разницу между `models.User` (БД) и `schemas.UserCreate` (валидация)
- [ ] Понимаю, как хешируются пароли и зачем это нужно
- [ ] Знаю, как работает JWT токен и `get_current_user()`
- [ ] Могу добавить новое поле в модель и схемы
- [ ] Могу создать новый endpoint
- [ ] Понимаю, как защитить endpoint через `Depends(get_current_user)`

---

Удачи в разработке! 🚀

