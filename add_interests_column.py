"""
Скрипт для добавления колонки interests_list в таблицу users
Использование: python add_interests_column.py
"""
import sqlite3
from pathlib import Path

def add_interests_column():
    """Добавляет колонку interests_list в таблицу users"""
    db_path = Path(__file__).parent / "users.db"
    
    if not db_path.exists():
        print(f"❌ База данных {db_path} не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже колонка
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'interests_list' in columns:
            print("✅ Колонка interests_list уже существует в таблице users")
            conn.close()
            return
        
        # Добавляем колонку
        cursor.execute("ALTER TABLE users ADD COLUMN interests_list TEXT")
        conn.commit()
        
        print("✅ Колонка interests_list успешно добавлена в таблицу users")
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при добавлении колонки: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    add_interests_column()

