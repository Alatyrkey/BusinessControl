from typing import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from app.config import settings


def _ensure_sqlite_dir_exists() -> None:
    """Создаёт папку для SQLite-базы, если её ещё нет."""
    if not settings.DATABASE_URL.startswith("sqlite:///"):
        return

    db_path = Path(
        settings.DATABASE_URL.removeprefix("sqlite:///")
    )
    db_dir = db_path.parent

    if db_dir:
        db_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


# Создаём директорию до инициализации движка
_ensure_sqlite_dir_exists()


# Разрешаем использовать SQLite-соединение в разных потоках
# Это нужно для работы SQLite с FastAPI
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}


# Создаём движок подключения к базе данных
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,  # Проверяет соединение перед использованием
)


# Включаем поддержку внешних ключей и каскадного удаления в SQLite
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection,
        connection_record,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Фабрика сессий базы данных
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Создаёт таблицы при старте приложения, если их ещё нет."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Возвращает сессию БД для одного запроса и закрывает её после."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()