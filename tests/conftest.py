import os

# Устанавливаем тестовую БД ДО импорта backend модулей
os.environ["DATABASE_URL"] = "sqlite:///./test_spreadscope.db"

from backend.database import Base, engine  # noqa: E402
from backend.models import User, WatchlistItem  # noqa: E402, F401

# Пересоздаём таблицы для чистого состояния
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
