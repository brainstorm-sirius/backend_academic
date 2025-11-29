import csv
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Author, AuthorInterest

Base.metadata.create_all(bind=engine)


def import_authors_csv(db: Session, csv_path: str, batch_size: int = 1000):
    print(f"Начинаю импорт {csv_path}...")
    
    count = 0
    batch = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            author = Author(
                pmid=row.get('PMID') or None,
                title=row.get('Title') or None,
                authors_original=row.get('Authors_Original') or None,
                citation=row.get('Citation') or None,
                journal_book=row.get('Journal/Book') or None,
                publication_year=row.get('Publication Year') or None,
                create_date=row.get('Create Date') or None,
                pmcid=row.get('PMCID') or None,
                nihms_id=row.get('NIHMS ID') or None,
                doi=row.get('DOI') or None,
                author_name=row.get('Author_Name') or None,
                author_id=row.get('Author_ID') or None,
            )
            batch.append(author)
            count += 1
            
            if len(batch) >= batch_size:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
                print(f"Импортировано {count} записей...")
    
    if batch:
        db.bulk_save_objects(batch)
        db.commit()
    
    print(f"Импорт завершён! Всего импортировано {count} записей авторов.")


def import_interests_csv(db: Session, csv_path: str, batch_size: int = 1000):
    print(f"Начинаю импорт {csv_path}...")
    
    count = 0
    skipped = 0
    duplicates = 0
    batch = []
    row_num = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            row_num += 1
            
            author_id = row.get('Author_ID', '').strip() if row.get('Author_ID') else ''
            
            if row_num <= 3:
                print(f"Отладка строка {row_num}: Author_ID = '{author_id}' (тип: {type(author_id)}, длина: {len(author_id)})")
                print(f"  Все ключи в row: {list(row.keys())}")
                print(f"  Значение row.get('Author_ID'): '{row.get('Author_ID')}'")
            
            if not author_id:
                skipped += 1
                if skipped <= 5:
                    print(f"Пропущена строка {row_num}: пустой Author_ID")
                continue
            
            interest = AuthorInterest(
                author_id=author_id,
                author_name=row.get('Author_Name') or None,
                interests_list=row.get('Interests_List') or None,
                keywords_list=row.get('Keywords_List') or None,
                interests_count=int(row['Interests_Count']) if row.get('Interests_Count') and str(row['Interests_Count']).strip().isdigit() else None,
                articles_count=int(row['Articles_Count']) if row.get('Articles_Count') and str(row['Articles_Count']).strip().isdigit() else None,
                main_interest=row.get('Main_Interest') or None,
                cluster=int(row['Cluster']) if row.get('Cluster') and str(row['Cluster']).strip().isdigit() else None,
            )
            batch.append(interest)
            count += 1
            
            if len(batch) >= batch_size:
                try:
                    db.bulk_save_objects(batch)
                    db.commit()
                    batch = []
                    print(f"Импортировано {count} записей... (пропущено {skipped}, дубликатов {duplicates})")
                except Exception as e:
                    db.rollback()
                    if "UNIQUE constraint" in str(e) or "IntegrityError" in str(type(e).__name__):
                        print(f"Обнаружены дубликаты, переключаюсь на поштучную вставку...")
                        for item in batch:
                            try:
                                db.add(item)
                                db.commit()
                            except Exception as dup_error:
                                db.rollback()
                                if "UNIQUE constraint" in str(dup_error) or "IntegrityError" in str(type(dup_error).__name__):
                                    duplicates += 1
                                    count -= 1
                                else:
                                    raise
                    else:
                        print(f"Ошибка при вставке: {e}")
                        raise
                    batch = []
    
    if batch:
        try:
            db.bulk_save_objects(batch)
            db.commit()
        except Exception as e:
            db.rollback()
            if "UNIQUE constraint" in str(e) or "IntegrityError" in str(type(e).__name__):
                for item in batch:
                    try:
                        db.add(item)
                        db.commit()
                    except Exception as dup_error:
                        db.rollback()
                        if "UNIQUE constraint" in str(dup_error) or "IntegrityError" in str(type(dup_error).__name__):
                            duplicates += 1
                            count -= 1
                        else:
                            raise
            else:
                raise
    
    print(f"Импорт завершён! Всего импортировано {count} записей научных интересов.")
    if skipped > 0:
        print(f"Пропущено {skipped} записей без Author_ID.")
    if duplicates > 0:
        print(f"Пропущено {duplicates} дубликатов (author_id уже существует).")


def main():
    db = SessionLocal()
    
    try:
        base_dir = Path(__file__).parent
        authors_csv = base_dir / "authors_expanded_with_ids.csv"
        interests_csv = base_dir / "authors_scientific_interests.csv"
        
        if not authors_csv.exists():
            print(f"Файл {authors_csv} не найден!")
            return
        
        if not interests_csv.exists():
            print(f"Файл {interests_csv} не найден!")
            return
        
        print("=" * 60)
        print("Начинаю импорт CSV файлов в базу данных...")
        print("=" * 60)
        
        print("\nИмпорт авторов и статей...")
        import_authors_csv(db, str(authors_csv))
        
        print("\nИмпорт научных интересов...")
        import_interests_csv(db, str(interests_csv))
        
        print("\n" + "=" * 60)
        print("Импорт всех данных завершён успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Ошибка при импорте: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

