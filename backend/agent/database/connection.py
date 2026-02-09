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

# Database configuration from environment
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")
DB_NAME = os.getenv("PGDATABASE", "postgres")
DB_USER = os.getenv("PGUSER", "WestBrandService")
DB_PASSWORD = os.getenv("PGPASSWORD", "")

# Construct connection string
DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


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
