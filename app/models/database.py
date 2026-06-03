"""
MedFlow Imaging — SQLAlchemy Database Engine & Session

Connects to the existing MSSQL database using pyodbc.
Provides a get_db() dependency for FastAPI route injection.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.config import settings

# Create the SQLAlchemy engine connected to MSSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",  # Log SQL queries in dev mode
    pool_pre_ping=True,                       # Verify connections before use
    pool_size=10,
    max_overflow=20,
)

# Session factory — each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Automatically closes the session when the request completes.

    Usage in routes:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
