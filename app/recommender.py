"""
Модуль для рекомендаций учёных по интересам
Использует обученную ML модель для поиска похожих авторов
"""
import os
import pickle
import re
import logging
from typing import List, Optional
from collections import Counter

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from scipy import sparse

logger = logging.getLogger(__name__)


class CollaborationRecommender:
    """Класс для рекомендации учёных на основе их научных интересов"""
    
    def __init__(self):
        self.df = None
        self.vectorizer = None
        self.author_vectors = None
        self.knn_model = None
        self.max_articles = 1
        self.max_interests = 1
        
    def load_model(self, model_path: str = "model"):
        """
        Загружает обученную модель из указанной папки
        
        Args:
            model_path: Путь к папке с моделью
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path {model_path} does not exist")
            
        try:
            with open(os.path.join(model_path, "authors_data.pkl"), 'rb') as f:
                self.df = pickle.load(f)
            
            with open(os.path.join(model_path, "vectorizer.pkl"), 'rb') as f:
                self.vectorizer = pickle.load(f)
                
            self.author_vectors = sparse.load_npz(os.path.join(model_path, "author_vectors.npz"))
            
            with open(os.path.join(model_path, "knn_model.pkl"), 'rb') as f:
                self.knn_model = pickle.load(f)
                
            self.max_articles = self.df['Articles_Count'].max() if 'Articles_Count' in self.df.columns else 1
            self.max_interests = self.df['Interests_Count'].max() if 'Interests_Count' in self.df.columns else 1
            
            logger.info(f"Loaded model with {len(self.df)} authors")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def _create_target_profile(self, interests_list: List[str], publications_list: Optional[List[str]] = None) -> str:
        """
        Создаёт профиль пользователя на основе интересов и публикаций
        
        Args:
            interests_list: Список научных интересов
            publications_list: Опциональный список публикаций
            
        Returns:
            Строка профиля для векторизации
        """
        profile_parts = interests_list.copy()
        
        if publications_list:
            all_text = ' '.join([str(pub) for pub in publications_list])
            words = re.findall(r'\b[a-z]{4,}\b', all_text.lower())
            stop_words = {'research', 'study', 'analysis', 'method', 'results', 'conclusion'}
            filtered_words = [word for word in words if word not in stop_words]
            keywords = [word for word, count in Counter(filtered_words).most_common(10)]
            profile_parts.extend(keywords)
        
        return ' '.join(profile_parts)

    def recommend(self, interests: List[str], publications: Optional[List[str]] = None, top_k: int = 10) -> List[dict]:
        """
        Получает рекомендации учёных на основе интересов
        
        Args:
            interests: Список научных интересов пользователя
            publications: Опциональный список публикаций для анализа
            top_k: Количество рекомендаций
            
        Returns:
            Список словарей с рекомендациями, отсортированный по total_score
        """
        if self.df is None or self.vectorizer is None or self.knn_model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        target_profile = self._create_target_profile(interests, publications)
        target_vector = self.vectorizer.transform([target_profile])
        
        n_neighbors = min(top_k * 10, len(self.df))
        distances, indices = self.knn_model.kneighbors(target_vector, n_neighbors=n_neighbors)
        similarities = 1 - distances.flatten()
        
        recommendations = []
        
        for similarity, idx in zip(similarities, indices[0]):
            if similarity < 0.1:
                continue
                
            author_data = self.df.iloc[idx]
            
            # Нормализуем метрики
            productivity_score = author_data['Articles_Count'] / self.max_articles if self.max_articles > 0 else 0
            diversity_score = author_data['Interests_Count'] / self.max_interests if self.max_interests > 0 else 0
            
            # Комбинированный скор
            total_score = (
                similarity * 0.6 +
                productivity_score * 0.25 +
                diversity_score * 0.15
            )
            
            recommendations.append({
                'author_id': str(author_data['Author_ID']),
                'author_name': str(author_data['Author_Name']) if pd.notna(author_data['Author_Name']) else "Unknown",
                'total_score': float(total_score),
                'similarity_score': float(similarity),
                'productivity_score': float(productivity_score),
                'diversity_score': float(diversity_score),
                'articles_count': int(author_data['Articles_Count']) if pd.notna(author_data['Articles_Count']) else 0,
                'interests_count': int(author_data['Interests_Count']) if pd.notna(author_data['Interests_Count']) else 0,
                'main_interest': str(author_data.get('Main_Interest')) if pd.notna(author_data.get('Main_Interest')) else None
            })
            
            if len(recommendations) >= top_k:
                break
        
        # Сортируем по total_score и возвращаем top_k
        return sorted(recommendations, key=lambda x: x['total_score'], reverse=True)[:top_k]

