"""
Database connection management and session handling.

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI endpoints.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from backend.config import get_settings
from backend.models.database_models import Base

logger = logging.getLogger(__name__)

# Get configuration
settings = get_settings()

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_pool_max_overflow,
    pool_pre_ping=True,  # Verify connections before using
    echo=not settings.is_production  # Log SQL in development
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Yields a SQLAlchemy session and ensures it's closed after use.
    Use with FastAPI's Depends() for automatic session management.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            # Use db here
            pass

    Yields:
        Session: SQLAlchemy database session

    Example:
        db = next(get_db())
        try:
            # Use db
            pass
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This is typically not used in production (use migrations instead),
    but useful for initial setup or testing.

    Note:
        In production, use Alembic migrations for schema changes.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False
