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
import time

from backend.config import get_settings
from backend.models.database_models import Base

logger = logging.getLogger(__name__)

# Get configuration
settings = get_settings()

# Create SQLAlchemy engine with connection pooling for better performance
# Using QueuePool instead of NullPool to reuse connections and avoid SSL overhead
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,  # Keep 5 connections in the pool
    max_overflow=10,  # Allow up to 10 additional connections
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    pool_recycle=300,  # Recycle connections after 5 minutes to avoid stale SSL
    pool_pre_ping=True,  # Verify connections before using
    echo=not settings.is_production,  # Log SQL in development
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI with retry logic.

    Yields a SQLAlchemy session and ensures it's closed after use.
    Includes retry logic for transient connection failures (SSL errors).

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            # Use db here
            pass

    Yields:
        Session: SQLAlchemy database session
    """
    max_retries = 3
    retry_delay = 0.5  # seconds
    last_error = None

    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test the connection with a simple query
            db.execute(text("SELECT 1"))
            try:
                yield db
            except Exception as e:
                logger.error(f"Database session error during request: {str(e)}")
                db.rollback()
                raise
            finally:
                db.close()
            return  # Successfully completed
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            is_connection_error = any(term in error_msg for term in
                ['ssl', 'connection', 'timeout', 'closed', 'refused', 'reset'])

            if is_connection_error and attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying: {str(e)}")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue

            logger.error(f"Database connection failed after {attempt + 1} attempts: {str(e)}")
            raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error


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
