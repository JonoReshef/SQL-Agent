"""Database connection management for WestBrand system"""

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Load environment variables
load_dotenv()


def _get_database_url() -> str:
    """
    Get database URL, preferring DATABASE_URL env var if set,
    otherwise constructing from individual PG* variables.
    """
    # Prefer explicit DATABASE_URL (used in Docker/production)
    if url := os.getenv("DATABASE_URL"):
        # Ensure we use psycopg driver
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    # Fall back to individual PG* variables (local development)
    db_host = os.getenv("PGHOST", "localhost")
    db_port = os.getenv("PGPORT", "5432")
    db_name = os.getenv("PGDATABASE", "postgres")
    db_user = os.getenv("PGUSER", "WestBrandService")
    db_password = os.getenv("PGPASSWORD", "")

    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = _get_database_url()


def get_engine(echo: bool = False) -> Engine:
    """
    Create and return a SQLAlchemy engine.

    Args:
        echo: If True, SQL statements will be logged

    Returns:
        SQLAlchemy Engine instance
    """
    return create_engine(
        DATABASE_URL,
        echo=echo,
        poolclass=NullPool,  # Disable connection pooling for simplicity
    )


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Args:
        engine: Optional engine to use. If None, creates a new one.

    Yields:
        SQLAlchemy Session

    Example:
        with get_db_session() as session:
            session.query(ProductMention).all()
    """
    if engine is None:
        engine = get_engine()

    SessionLocal.configure(bind=engine)
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
