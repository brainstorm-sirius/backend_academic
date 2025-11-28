import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from scipy import sparse
import pickle
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self, data_path: str, model_save_path: str = "model"):
        self.data_path = data_path
        self.model_save_path = model_save_path
        self.df = None
        self.vectorizer = None
        self.author_vectors = None
        self.knn_model = None
        
    def load_data(self):
        self.df = pd.read_csv(self.data_path)
        
        if 'Interests_List' in self.df.columns:
            self.df['Interests_List_Clean'] = self.df['Interests_List'].apply(
                lambda x: [interest.strip() for interest in x.split('|')] if isinstance(x, str) else []
            )
        else:
            raise ValueError("Interests_List column not found in data")
            
        self.df['author_profile'] = self.df.apply(self._create_author_profile, axis=1)
        logger.info(f"Loaded data with {len(self.df)} authors")

    def _create_author_profile(self, row):
        profile_parts = []
        
        if pd.notna(row['Interests_List']):
            interests_text = ' '.join(row['Interests_List_Clean'])
            profile_parts.append(interests_text)
        
        if 'Keywords_List' in row and pd.notna(row['Keywords_List']):
            if isinstance(row['Keywords_List'], str):
                keywords = [kw.strip() for kw in row['Keywords_List'].split('|')]
                profile_parts.extend(keywords)
        
        if 'Main_Interest' in row and pd.notna(row['Main_Interest']):
            profile_parts.append(row['Main_Interest'])
        
        return ' '.join(profile_parts)

    def train_vectorizer(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=5,
            max_df=0.7
        )
        
        profiles = self.df['author_profile'].fillna('').tolist()
        self.author_vectors = self.vectorizer.fit_transform(profiles)
        logger.info(f"TF-IDF vectors created: {self.author_vectors.shape}")

    def train_knn(self):
        self.knn_model = NearestNeighbors(
            n_neighbors=min(1000, len(self.df)),
            metric='cosine',
            algorithm='brute',
            n_jobs=-1
        )
        self.knn_model.fit(self.author_vectors)
        logger.info("KNN model trained")

    def save_model(self):
        os.makedirs(self.model_save_path, exist_ok=True)
        
        with open(os.path.join(self.model_save_path, "authors_data.pkl"), 'wb') as f:
            pickle.dump(self.df, f)
            
        with open(os.path.join(self.model_save_path, "vectorizer.pkl"), 'wb') as f:
            pickle.dump(self.vectorizer, f)
            
        sparse.save_npz(os.path.join(self.model_save_path, "author_vectors.npz"), self.author_vectors)
        
        with open(os.path.join(self.model_save_path, "knn_model.pkl"), 'wb') as f:
            pickle.dump(self.knn_model, f)
            
        logger.info(f"Model saved to {self.model_save_path}")

    def train(self):
        self.load_data()
        self.train_vectorizer()
        self.train_knn()
        self.save_model()

if __name__ == "__main__":
    trainer = ModelTrainer("authors_scientific_interests.csv")
    trainer.train()