from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    google_scholar_id = Column(String(255))
    scopus_id = Column(String(255))
    wos_id = Column(String(255))
    rsci_id = Column(String(255))
    orcid_id = Column(String(255))
    interests_list = Column(Text, nullable=True)  # Список научных интересов пользователя
    password_hash = Column(String(255), nullable=False)
    
    # Связь с публикациями
    publications = relationship("UserPublication", back_populates="user", cascade="all, delete-orphan")


class Author(Base):
    """Незарегистрированные авторы со статьями"""
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    pmid = Column(String(50), index=True)
    title = Column(Text)
    authors_original = Column(Text)
    citation = Column(Text)
    journal_book = Column(String(500))
    publication_year = Column(String(10))
    create_date = Column(String(50))
    pmcid = Column(String(50))
    nihms_id = Column(String(50))
    doi = Column(String(255))
    author_name = Column(String(500), index=True)  # Для поиска по имени
    author_id = Column(String(100), index=True)  # Уникальный ID автора


class AuthorInterest(Base):
    """Научные интересы незарегистрированных авторов"""
    __tablename__ = "author_interests"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(String(100), unique=True, nullable=False, index=True)
    author_name = Column(String(500), index=True)  # Для поиска по имени
    interests_list = Column(Text)
    keywords_list = Column(Text)
    interests_count = Column(Integer)
    articles_count = Column(Integer)
    main_interest = Column(String(255))
    cluster = Column(Integer)


class UserPublication(Base):
    """Публикации зарегистрированных пользователей"""
    __tablename__ = "user_publications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Данные из файла
    title = Column(Text, nullable=False)  # Название статьи
    coauthors = Column(Text)  # Соавторы
    citations = Column(String(50))  # Цитирование
    journal = Column(String(500))  # Журнал
    publication_year = Column(String(10))  # Год публикации
    author_name = Column(String(500))  # Имя автора
    
    # Связь с пользователем
    user = relationship("User", back_populates="publications")
