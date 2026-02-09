"""Database schema initialization.

This module provides functions to create and manage the database schema.
"""

from sqlalchemy import create_engine

from workflow.database.connection import DATABASE_URL
from workflow.database.models import Base


def init_database() -> None:
    """Initialize the database by creating all tables if they don't exist.

    This function is idempotent - it's safe to call multiple times.
    Tables are created based on SQLAlchemy models defined in models.py.
    """
    engine = create_engine(DATABASE_URL)

    # Create all tables defined in Base metadata
    Base.metadata.create_all(engine)

    print("✅ Database schema initialized successfully")
    print(f"   Tables created: {', '.join(Base.metadata.tables.keys())}")


def drop_all_tables() -> None:
    """Drop all tables from the database.

    WARNING: This will delete all data! Use with caution.
    Only use in development/testing environments.
    """
    engine = create_engine(DATABASE_URL)

    # Drop all tables
    Base.metadata.drop_all(engine)

    print("⚠️  All tables dropped from database")


if __name__ == "__main__":
    # Initialize database when run as script
    init_database()
