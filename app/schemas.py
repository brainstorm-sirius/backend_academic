from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Union


class UserBase(BaseModel):
    login: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    first_name: str
    last_name: str
    google_scholar_id: Optional[str] = None
    scopus_id: Optional[str] = None
    wos_id: Optional[str] = None
    rsci_id: Optional[str] = None
    orcid_id: Optional[str] = None
    interests_list: Optional[str] = None  # Список научных интересов (через запятую)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    login_or_email: str
    password: str


class UpdateInterestsRequest(BaseModel):
    """Схема для обновления научных интересов пользователя"""
    login: str = Field(..., min_length=3, description="Login пользователя")
    interests_list: List[str] = Field(..., description="Список научных интересов")


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthorResponse(BaseModel):
    """Ответ для незарегистрированного автора"""
    id: int
    pmid: Optional[str] = None
    title: Optional[str] = None
    authors_original: Optional[str] = None
    citation: Optional[str] = None
    journal_book: Optional[str] = None
    publication_year: Optional[str] = None
    create_date: Optional[str] = None
    pmcid: Optional[str] = None
    nihms_id: Optional[str] = None
    doi: Optional[str] = None
    author_name: Optional[str] = None
    author_id: Optional[str] = None

    class Config:
        from_attributes = True


class AuthorInterestResponse(BaseModel):
    """Ответ для научных интересов автора"""
    id: int
    author_id: str
    author_name: Optional[str] = None
    interests_list: Optional[str] = None
    keywords_list: Optional[str] = None
    interests_count: Optional[int] = None
    articles_count: Optional[int] = None
    main_interest: Optional[str] = None
    cluster: Optional[int] = None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Ответ для поиска - объединяет зарегистрированных и незарегистрированных"""
    registered_users: List[UserResponse] = []
    unregistered_authors: List[AuthorResponse] = []
    author_interests: List[AuthorInterestResponse] = []


class Metric(BaseModel):
    """Метрика учёного"""
    label: str
    value: str


class ScientistInfo(BaseModel):
    """Информация об учёном"""
    username: str
    name: str
    affiliation: str
    orcid: str
    metrics: List[Metric]


class Analytics(BaseModel):
    """Аналитика"""
    index: float
    average: float
    performance: str


class TopicDistribution(BaseModel):
    """Распределение тем"""
    label: str
    value: int
    color: str


class Publication(BaseModel):
    """Публикация"""
    id: int
    title: str
    journal: str
    year: Union[int, str]  # Может быть int или "N/A"
    citations: Union[int, str]  # Может быть int или "N/A"
    summary: str  # Всегда строка, может быть "N/A"


class ScientistProfileResponse(BaseModel):
    """Полный профиль учёного"""
    scientist: ScientistInfo
    analytics: Analytics
    topicDistribution: List[TopicDistribution]
    publications: List[Publication]


class RecommendationRequest(BaseModel):
    """Запрос на рекомендации по интересам"""
    interests: List[str] = Field(..., description="Список научных интересов")
    publications: Optional[List[str]] = Field(None, description="Опциональный список публикаций для анализа")
    num_recommendations: int = Field(10, ge=1, le=100, description="Количество рекомендаций")


class AuthorRecommendation(BaseModel):
    """Рекомендация автора"""
    author_id: str
    author_name: str
    total_score: float
    similarity_score: float
    productivity_score: float
    diversity_score: float
    articles_count: int
    interests_count: int
    main_interest: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Ответ с рекомендациями"""
    recommendations: List[AuthorRecommendation]
    processing_time: float


class UserPublicationBase(BaseModel):
    """Базовая схема публикации пользователя"""
    title: str = Field(..., description="Название статьи")
    coauthors: Optional[str] = Field(None, description="Соавторы")
    citations: Optional[str] = Field(None, description="Цитирование")
    journal: Optional[str] = Field(None, description="Журнал")
    publication_year: Optional[str] = Field(None, description="Год публикации")
    author_name: Optional[str] = Field(None, description="Имя автора")


class UserPublicationCreate(UserPublicationBase):
    """Схема для создания публикации"""
    pass


class UserPublicationResponse(UserPublicationBase):
    """Схема ответа с публикацией"""
    id: int
    user_id: int

    class Config:
        from_attributes = True


class PublicationUploadResponse(BaseModel):
    """Ответ после загрузки публикаций"""
    message: str
    imported_count: int
    failed_count: int
    publications: List[UserPublicationResponse]
