import time
import logging
import io
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List
import pandas as pd

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

recommender = CollaborationRecommender()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_path = "model"
        recommender.load_model(model_path)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
    
    yield
    
    logger.info("Application shutdown")


# База данных создается через entrypoint.sh при инициализации
# Не создаем БД здесь, чтобы избежать проблем с правами доступа
# models.Base.metadata.create_all(bind=engine)

origins = [
    "http://academic.khokhlovkirill.ru",
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://frontend:5173",
    "http://academic_frontend:5173",
]

app = FastAPI(title="User Auth Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    login_exists = db.query(models.User).filter(models.User.login == payload.login).first()
    if login_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login already taken")

    email_exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if email_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    try:
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
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user account"
        )


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
    user = db.query(models.User).filter(models.User.login == payload.login).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с login '{payload.login}' не найден"
        )
    
    interests_string = ", ".join(payload.interests_list) if payload.interests_list else None
    
    try:
        user.interests_list = interests_string
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user interests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating interests"
        )


@app.post("/users/{user_id}/publications/upload", response_model=schemas.PublicationUploadResponse)
async def upload_publications(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_ROWS = 10000
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    contents = await file.read()
    
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    
    imported_count = 0
    failed_count = 0
    publications = []
    
    try:
        if file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        elif file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload Excel (.xlsx, .xls) or CSV (.csv) file"
            )
        
        column_mapping = {
            'название статьи': 'title',
            'название': 'title',
            'title': 'title',
            'ArticleTitle': 'title',
            'соавторы': 'coauthors',
            'coauthors': 'coauthors',
            'Co-authors': 'coauthors',
            'соавтор': 'coauthors',
            'цитирование': 'citations',
            'citations': 'citations',
            'Citations': 'citations',
            'цитаты': 'citations',
            'журнал': 'journal',
            'Source': 'journal',
            'journal': 'journal',
            'год публикации': 'publication_year',
            'год': 'publication_year',
            'year': 'publication_year',
            'publication_year': 'publication_year',
            'Year of Publication': 'publication_year',
            'имя автора': 'author_name',
            'author_name': 'author_name',
            'Author': 'author_name',
            'автор': 'author_name',
        }
        
        df.columns = df.columns.str.strip().str.lower()
        
        if len(df) > MAX_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File contains too many rows. Maximum allowed: {MAX_ROWS}"
            )
        
        title_column = None
        for col in df.columns:
            if col in ['название статьи', 'название', 'title']:
                title_column = col
                break
        
        if not title_column:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Required column 'Название статьи' (or 'Title') not found in file"
            )
        
        for index, row in df.iterrows():
            try:
                title = str(row[title_column]).strip() if pd.notna(row[title_column]) else None
                
                if not title or title == 'nan':
                    failed_count += 1
                    continue
                
                coauthors = None
                citations = None
                journal = None
                publication_year = None
                author_name = None
                
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if col_lower in ['соавторы', 'coauthors', 'соавтор']:
                        coauthors = str(row[col]).strip() if pd.notna(row[col]) else None
                    elif col_lower in ['цитирование', 'citations', 'цитаты']:
                        citations = str(row[col]).strip() if pd.notna(row[col]) else None
                    elif col_lower in ['журнал', 'journal']:
                        journal = str(row[col]).strip() if pd.notna(row[col]) else None
                    elif col_lower in ['год публикации', 'год', 'year', 'publication_year']:
                        publication_year = str(row[col]).strip() if pd.notna(row[col]) else None
                    elif col_lower in ['имя автора', 'author_name', 'автор']:
                        author_name = str(row[col]).strip() if pd.notna(row[col]) else None
                
                publication = models.UserPublication(
                    user_id=user_id,
                    title=title,
                    coauthors=coauthors,
                    citations=citations,
                    journal=journal,
                    publication_year=publication_year,
                    author_name=author_name
                )
                
                db.add(publication)
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error processing row {index}: {e}")
                failed_count += 1
                continue
        
        db.commit()
        
        user_publications = db.query(models.UserPublication).filter(
            models.UserPublication.user_id == user_id
        ).all()
        
        publications = [schemas.UserPublicationResponse.model_validate(pub) for pub in user_publications]
        
        return schemas.PublicationUploadResponse(
            message=f"Successfully imported {imported_count} publications",
            imported_count=imported_count,
            failed_count=failed_count,
            publications=publications
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading publications: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


@app.get("/users/{user_id}/publications", response_model=List[schemas.UserPublicationResponse])
def get_user_publications(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    publications = db.query(models.UserPublication).filter(
        models.UserPublication.user_id == user_id
    ).all()
    
    return publications


@app.delete("/users/{user_id}/publications/{publication_id}")
def delete_user_publication(
    user_id: int,
    publication_id: int,
    db: Session = Depends(get_db)
):
    publication = db.query(models.UserPublication).filter(
        models.UserPublication.id == publication_id,
        models.UserPublication.user_id == user_id
    ).first()
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found"
        )
    
    try:
        db.delete(publication)
        db.commit()
        return {"message": "Publication deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting publication: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting publication"
        )


@app.get("/search", response_model=schemas.SearchResponse)
def search_users_and_authors(
    query: str = Query(..., min_length=2, description="Поисковый запрос (username или имя автора)"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    db: Session = Depends(get_db)
):
    search_term = f"%{query.lower()}%"
    
    registered_users = (
        db.query(models.User)
        .filter(
            func.lower(models.User.login).like(search_term)
        )
        .limit(limit)
        .all()
    )
    
    unregistered_authors = (
        db.query(models.Author)
        .filter(
            func.lower(models.Author.author_name).like(search_term)
        )
        .limit(limit)
        .all()
    )
    
    author_ids = [author.author_id for author in unregistered_authors if author.author_id]
    
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
    
    publications_list = (
        db.query(models.Author)
        .filter(models.Author.author_id == author_id)
        .all()
    )
    
    registered_user = None
    if interest.author_id:
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
    
    if registered_user:
        username = registered_user.login
    elif interest.author_name:
        name_parts = interest.author_name.split()
        if name_parts:
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
    affiliation = "N/A"
    orcid = registered_user.orcid_id if registered_user and registered_user.orcid_id else "N/A"
    
    articles_count = interest.articles_count if interest.articles_count else len(publications_list) if publications_list else 0
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
    
    if interest.interests_count and interest.articles_count:
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
    
    topic_distribution = []
    colors = ["#5BC0F8", "#7C3AED", "#F2A541", "#142850", "#38B2AC", "#EC4899", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    
    if interest.interests_list:
        interests = [i.strip() for i in interest.interests_list.split(',') if i.strip()]
        
        if interests:
            base_value = articles_count // len(interests) if articles_count > 0 else 1
            remainder = articles_count % len(interests) if articles_count > 0 else 0
            
            for idx, interest_name in enumerate(interests):
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
    
    if not topic_distribution:
        main_interest_label = interest.main_interest if interest.main_interest else "Other"
        topic_distribution.append(
            schemas.TopicDistribution(
                label=main_interest_label,
                value=articles_count if articles_count > 0 else 1,
                color=colors[0]
            )
        )
    
    publications = []
    for idx, pub in enumerate(publications_list, start=1):
        year = None
        if pub.publication_year:
            try:
                year = int(str(pub.publication_year).strip())
            except (ValueError, TypeError):
                pass
        
        citations = None
        
        summary = "N/A"
        if pub.citation:
            summary = pub.citation
        elif pub.title:
            summary = pub.title
        
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
    
    return schemas.ScientistProfileResponse(
        scientist=scientist_info,
        analytics=analytics,
        topicDistribution=topic_distribution,
        publications=publications
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "authors_count": len(recommender.df) if recommender.df is not None else 0,
        "model_loaded": recommender.df is not None and recommender.knn_model is not None
    }


@app.post("/recommend", response_model=schemas.RecommendationResponse)
async def get_recommendations(request: schemas.RecommendationRequest):
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


@app.get("/knowledge-graph", response_model=schemas.KnowledgeGraphResponse)
def get_knowledge_graph(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        users = db.query(models.User).filter(models.User.interests_list.isnot(None)).all()
        interest_to_users = defaultdict(set)
        
        for user in users:
            if user.interests_list:
                interests = [i.strip() for i in user.interests_list.split(',') if i.strip()]
                for interest in interests:
                    interest_to_users[interest].add(f"user_{user.id}")
        
        author_interests_list = db.query(models.AuthorInterest).filter(
            models.AuthorInterest.interests_list.isnot(None)
        ).all()
        
        for ai in author_interests_list:
            if ai.interests_list:
                interests = [i.strip() for i in ai.interests_list.split(',') if i.strip()]
                for interest in interests:
                    interest_to_users[interest].add(f"author_{ai.id}")
        
        unique_interests = sorted(interest_to_users.keys())
        interest_id_map = {interest: idx + 1 for idx, interest in enumerate(unique_interests)}
        
        interest_counts = {interest: len(interest_to_users[interest]) for interest in unique_interests}
        
        interests_list = [
            schemas.InterestNode(
                id=interest_id_map[interest],
                name=interest,
                scientist_count=interest_counts[interest]
            )
            for interest in unique_interests
        ]
        
        current_user_interests = []
        if current_user.interests_list:
            current_user_interests = [i.strip() for i in current_user.interests_list.split(',') if i.strip()]
        
        all_users = db.query(models.User).filter(models.User.id != current_user.id).all()
        user_scientists_with_scores = []
        
        for user in all_users:
            user_interests_ids = []
            user_interest_list = []
            if user.interests_list:
                user_interest_list = [i.strip() for i in user.interests_list.split(',') if i.strip()]
                for interest in user_interest_list:
                    if interest in interest_id_map:
                        user_interests_ids.append(interest_id_map[interest])
            
            username = user.login if user.login else f"{user.first_name}{user.last_name}"
            name = f"{user.first_name} {user.last_name}"
            
            similarity_score = 0.0
            if current_user_interests and user_interest_list:
                common_interests = set(current_user_interests) & set(user_interest_list)
                total_interests = set(current_user_interests) | set(user_interest_list)
                if total_interests and len(total_interests) > 0:
                    similarity_score = len(common_interests) / len(total_interests)
            
            user_scientists_with_scores.append({
                'id': user.id,
                'name': name,
                'username': username,
                'interests': user_interests_ids,
                'type': 'user',
                'score': similarity_score
            })
        
        author_scientists_with_scores = []
        
        if current_user_interests and recommender.df is not None and recommender.knn_model is not None:
            try:
                ml_recommendations = recommender.recommend(
                    interests=current_user_interests,
                    top_k=100
                )
                recommended_author_ids = {rec['author_id'] for rec in ml_recommendations}
                recommendation_scores = {rec['author_id']: rec['total_score'] for rec in ml_recommendations}
            except Exception as e:
                logger.warning(f"Recommendation failed, using fallback: {e}")
                recommended_author_ids = set()
                recommendation_scores = {}
        else:
            recommended_author_ids = set()
            recommendation_scores = {}
        
        all_author_interests = db.query(models.AuthorInterest).all()
        for ai in all_author_interests:
            author_interests_ids = []
            author_interest_list = []
            if ai.interests_list:
                author_interest_list = [i.strip() for i in ai.interests_list.split(',') if i.strip()]
                for interest in author_interest_list:
                    if interest in interest_id_map:
                        author_interests_ids.append(interest_id_map[interest])
            
            author_name = ai.author_name if ai.author_name else "Unknown"
            name_parts = author_name.split()
            username = "".join([part.replace(".", "").replace(",", "")[:5] for part in name_parts[:2]]) if name_parts else author_name[:10]
            
            similarity_score = 0.0
            if current_user_interests and author_interest_list:
                common_interests = set(current_user_interests) & set(author_interest_list)
                total_interests = set(current_user_interests) | set(author_interest_list)
                if total_interests and len(total_interests) > 0:
                    similarity_score = len(common_interests) / len(total_interests)
            
            if ai.author_id in recommended_author_ids:
                similarity_score = max(similarity_score, recommendation_scores.get(ai.author_id, 0.0))
            
            author_scientists_with_scores.append({
                'id': ai.id + 100000,
                'name': author_name,
                'username': username,
                'interests': author_interests_ids,
                'type': 'author',
                'score': similarity_score
            })
        
        all_scientists = user_scientists_with_scores + author_scientists_with_scores
        all_scientists.sort(key=lambda x: x['score'], reverse=True)
        selected_scientists = all_scientists[:min(100, len(all_scientists))]
        
        scientists_list = [
            schemas.ScientistNode(
                id=scientist['id'],
                name=scientist['name'],
                username=scientist['username'],
                interests=scientist['interests']
            )
            for scientist in selected_scientists
        ]
        
        return schemas.KnowledgeGraphResponse(
            interests=interests_list,
            scientists=scientists_list
        )
        
    except Exception as e:
        logger.error(f"Error generating knowledge graph: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating knowledge graph: {str(e)}"
        )
