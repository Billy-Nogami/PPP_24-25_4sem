import os
import sys
from app.db.session import engine
from app.models.user import User
from app.models.task import Base

def create_tables():
    print("Создание таблиц в базе данных...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    # Добавляем корень проекта в путь
    sys.path.append(os.getcwd())
    create_tables()