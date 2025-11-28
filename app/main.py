import time
import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List

from . import models, schemas
from .auth import (
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
    verify_password,
)
from .database import engine
from .recommender import CollaborationRecommender

logger = logging.getLogger(__name__)

# Глобальный экземпляр рекомендателя
recommender = CollaborationRecommender()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения: загрузка модели при старте"""
    # Startup: загружаем модель
    try:
        model_path = "model"
        recommender.load_model(model_path)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # Не прерываем запуск, но логируем ошибку
        # Приложение может работать без модели, но рекомендации не будут доступны
    
    yield
    
    # Shutdown: очистка ресурсов (если нужно)
    logger.info("Application shutdown")


models.Base.metadata.create_all(bind=engine)

# CORS настройки для работы с frontend
origins = [
    "http://localhost",
    "http://localhost:5173",  # Vite default port
    "http://localhost:3000",  # React default port
    "http://localhost:8080",  # Vue default port
]

app = FastAPI(title="User Auth Service", lifespan=lifespan)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    login_exists = db.query(models.User).filter(models.User.login == payload.login).first()
    if login_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login already taken")

    email_exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if email_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = models.User(
        login=payload.login,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        google_scholar_id=payload.google_scholar_id,
        scopus_id=payload.scopus_id,
        wos_id=payload.wos_id,
        rsci_id=payload.rsci_id,
        orcid_id=payload.orcid_id,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(
            (models.User.login == payload.login_or_email)
            | (models.User.email == payload.login_or_email)
        )
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token)


@app.get("/users/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.put("/users/interests", response_model=schemas.UserResponse)
def update_user_interests(
    payload: schemas.UpdateInterestsRequest,
    db: Session = Depends(get_db)
):
    """
    Обновить научные интересы пользователя по login
    Принимает login и список интересов, сохраняет их как строку через запятую
    """
    # Находим пользователя по login
    user = db.query(models.User).filter(models.User.login == payload.login).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с login '{payload.login}' не найден"
        )
    
    # Преобразуем список интересов в строку через запятую
    interests_string = ", ".join(payload.interests_list) if payload.interests_list else None
    
    # Обновляем interests_list
    user.interests_list = interests_string
    
    db.commit()
    db.refresh(user)
    
    return user


@app.get("/search", response_model=schemas.SearchResponse)
def search_users_and_authors(
    query: str = Query(..., min_length=2, description="Поисковый запрос (username или имя автора)"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    db: Session = Depends(get_db)
):
    """
    Поиск по зарегистрированным пользователям (по username) и незарегистрированным авторам (по имени)
    """
    search_term = f"%{query.lower()}%"
    
    # Поиск зарегистрированных пользователей по username
    registered_users = (
        db.query(models.User)
        .filter(
            func.lower(models.User.login).like(search_term)
        )
        .limit(limit)
        .all()
    )
    
    # Поиск незарегистрированных авторов по имени
    unregistered_authors = (
        db.query(models.Author)
        .filter(
            func.lower(models.Author.author_name).like(search_term)
        )
        .limit(limit)
        .all()
    )
    
    # Получаем author_id из найденных авторов для поиска их интересов
    author_ids = [author.author_id for author in unregistered_authors if author.author_id]
    
    # Поиск научных интересов для найденных авторов
    author_interests = []
    if author_ids:
        author_interests = (
            db.query(models.AuthorInterest)
            .filter(models.AuthorInterest.author_id.in_(author_ids))
            .all()
        )
    
    return schemas.SearchResponse(
        registered_users=registered_users,
        unregistered_authors=unregistered_authors,
        author_interests=author_interests
    )


@app.get("/search/users", response_model=List[schemas.UserResponse])
def search_registered_users(
    username: str = Query(..., min_length=2, description="Username для поиска"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    db: Session = Depends(get_db)
):
    """
    Поиск только по зарегистрированным пользователям по username
    """
    search_term = f"%{username.lower()}%"
    
    users = (
        db.query(models.User)
        .filter(func.lower(models.User.login).like(search_term))
        .limit(limit)
        .all()
    )
    
    return users


@app.get("/search/authors", response_model=List[schemas.AuthorResponse])
def search_unregistered_authors(
    name: str = Query(..., min_length=2, description="Имя автора для поиска"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    db: Session = Depends(get_db)
):
    """
    Поиск только по незарегистрированным авторам по имени
    """
    search_term = f"%{name.lower()}%"
    
    authors = (
        db.query(models.Author)
        .filter(func.lower(models.Author.author_name).like(search_term))
        .limit(limit)
        .all()
    )
    
    return authors


@app.get("/authors/{author_id}/interests", response_model=schemas.AuthorInterestResponse)
def get_author_interests(
    author_id: str,
    db: Session = Depends(get_db)
):
    """
    Получить научные интересы автора по его author_id
    """
    interest = (
        db.query(models.AuthorInterest)
        .filter(models.AuthorInterest.author_id == author_id)
        .first()
    )
    
    if not interest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Научные интересы для автора с ID {author_id} не найдены"
        )
    
    return interest


@app.get("/authors/{author_id}/profile", response_model=schemas.ScientistProfileResponse)
def get_scientist_profile(
    author_id: str,
    db: Session = Depends(get_db)
):
    """
    Получить полный профиль учёного по author_id
    Собирает данные из таблиц authors и author_interests
    """
    # Получаем научные интересы автора
    interest = (
        db.query(models.AuthorInterest)
        .filter(models.AuthorInterest.author_id == author_id)
        .first()
    )
    
    if not interest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Автор с ID {author_id} не найден"
        )
    
    # Получаем все публикации автора
    publications_list = (
        db.query(models.Author)
        .filter(models.Author.author_id == author_id)
        .all()
    )
    
    # Пытаемся найти зарегистрированного пользователя по ORCID или другим ID
    # (если author_id совпадает с каким-то ID в таблице users)
    registered_user = None
    if interest.author_id:
        # Пробуем найти по orcid_id, google_scholar_id и т.д.
        registered_user = (
            db.query(models.User)
            .filter(
                (models.User.orcid_id == interest.author_id)
                | (models.User.google_scholar_id == interest.author_id)
                | (models.User.scopus_id == interest.author_id)
                | (models.User.wos_id == interest.author_id)
                | (models.User.rsci_id == interest.author_id)
            )
            .first()
        )
    
    # Формируем данные учёного
    # Username: используем login зарегистрированного пользователя или генерируем из author_name
    if registered_user:
        username = registered_user.login
    elif interest.author_name:
        # Генерируем username из author_name
        name_parts = interest.author_name.split()
        if name_parts:
            # Берём первую часть имени и делаем username-подобным
            first_part = name_parts[0].replace(".", "").replace(",", "").strip()
            if len(name_parts) > 1:
                last_part = name_parts[-1].replace(".", "").replace(",", "").strip()[:5]
                username = first_part + last_part if first_part and last_part else first_part or "N/A"
            else:
                username = first_part if first_part else "N/A"
        else:
            username = "N/A"
    else:
        username = "N/A"
    
    name = interest.author_name if interest.author_name else "N/A"
    affiliation = "N/A"  # В таблицах нет поля affiliation
    orcid = registered_user.orcid_id if registered_user and registered_user.orcid_id else "N/A"
    
    # Метрики
    articles_count = interest.articles_count if interest.articles_count else len(publications_list) if publications_list else 0
    # H-Index и Citations пока не вычисляем, используем "N/A"
    metrics = [
        schemas.Metric(label="H-Index", value="N/A"),
        schemas.Metric(label="Citations", value="N/A"),
        schemas.Metric(label="Publications", value=str(articles_count) if articles_count > 0 else "0")
    ]
    
    scientist_info = schemas.ScientistInfo(
        username=username,
        name=name,
        affiliation=affiliation,
        orcid=orcid,
        metrics=metrics
    )
    
    # Аналитика (генерируем на основе данных)
    # Используем articles_count и interests_count для расчёта индекса
    if interest.interests_count and interest.articles_count:
        # Простая формула: среднее между количеством интересов и статей, нормализованное
        base_value = (interest.interests_count + interest.articles_count) / 2.0
        index = round(base_value * 0.4, 1)  # Нормализуем до разумного диапазона
        average = round(base_value * 0.45, 1)
    else:
        index = 0.0
        average = 0.0
    performance = "Overall Performance"
    
    analytics = schemas.Analytics(
        index=index,
        average=average,
        performance=performance
    )
    
    # Распределение тем (topicDistribution)
    # Парсим interests_list (формат: "Interest1,Interest2" или просто "Interest1")
    topic_distribution = []
    colors = ["#5BC0F8", "#7C3AED", "#F2A541", "#142850", "#38B2AC", "#EC4899", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    
    if interest.interests_list:
        interests = [i.strip() for i in interest.interests_list.split(',') if i.strip()]
        
        if interests:
            # Распределяем статьи между интересами
            base_value = articles_count // len(interests) if articles_count > 0 else 1
            remainder = articles_count % len(interests) if articles_count > 0 else 0
            
            for idx, interest_name in enumerate(interests):
                # Распределяем остаток по первым темам
                value = base_value + (1 if idx < remainder else 0)
                if value == 0:
                    value = 1  # Минимум 1
                
                color = colors[idx % len(colors)]
                topic_distribution.append(
                    schemas.TopicDistribution(
                        label=interest_name,
                        value=value,
                        color=color
                    )
                )
    
    # Если нет интересов в списке, используем main_interest
    if not topic_distribution:
        main_interest_label = interest.main_interest if interest.main_interest else "Other"
        topic_distribution.append(
            schemas.TopicDistribution(
                label=main_interest_label,
                value=articles_count if articles_count > 0 else 1,
                color=colors[0]
            )
        )
    
    # Публикации
    publications = []
    for idx, pub in enumerate(publications_list, start=1):
        # Год публикации
        year = None
        if pub.publication_year:
            try:
                year = int(str(pub.publication_year).strip())
            except (ValueError, TypeError):
                pass
        
        # Количество цитирований - пока не извлекаем, используем None (будет "N/A" в JSON)
        citations = None
        
        # Summary - используем citation, если есть, иначе часть title
        summary = "N/A"
        if pub.citation:
            summary = pub.citation
        elif pub.title:
            summary = pub.title
        
        # Ограничиваем длину summary
        if summary and len(summary) > 200:
            summary = summary[:197] + "..."
        
        publications.append(
            schemas.Publication(
                id=idx,
                title=pub.title if pub.title else "N/A",
                journal=pub.journal_book if pub.journal_book else "N/A",
                year=year if year is not None else "N/A",
                citations=citations if citations is not None else "N/A",
                summary=summary if summary else "N/A"
            )
        )
    
    # Если нет публикаций, возвращаем пустой список
    
    return schemas.ScientistProfileResponse(
        scientist=scientist_info,
        analytics=analytics,
        topicDistribution=topic_distribution,
        publications=publications
    )


@app.get("/health")
async def health_check():
    """
    Проверка здоровья приложения и статуса модели
    """
    return {
        "status": "healthy",
        "authors_count": len(recommender.df) if recommender.df is not None else 0,
        "model_loaded": recommender.df is not None and recommender.knn_model is not None
    }


@app.post("/recommend", response_model=schemas.RecommendationResponse)
async def get_recommendations(request: schemas.RecommendationRequest):
    """
    Получить рекомендации учёных на основе научных интересов
    
    Принимает список интересов и опционально список публикаций,
    возвращает топ учёных, отсортированных по релевантности
    """
    try:
        if recommender.df is None or recommender.knn_model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Recommendation model is not loaded. Please check server logs."
            )
        
        start_time = time.time()
        
        recommendations = recommender.recommend(
            interests=request.interests,
            publications=request.publications,
            top_k=request.num_recommendations
        )
        
        processing_time = time.time() - start_time
        
        # Преобразуем в схемы Pydantic
        recommendation_objects = [
            schemas.AuthorRecommendation(**rec) for rec in recommendations
        ]
        
        return schemas.RecommendationResponse(
            recommendations=recommendation_objects,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )
