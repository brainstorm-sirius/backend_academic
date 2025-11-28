"""
Скрипт для создания таблицы user_publications в базе данных
Использование: python add_publications_table.py
"""
from app.database import engine, Base
from app.models import UserPublication

def create_publications_table():
    """Создаёт таблицу user_publications в базе данных"""
    try:
        # Создаём таблицу
        UserPublication.__table__.create(bind=engine, checkfirst=True)
        print("✅ Таблица user_publications успешно создана")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
        raise

if __name__ == "__main__":
    create_publications_table()

