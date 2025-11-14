#!/usr/bin/env python3
"""
Database Setup Script

Initializes the WestBrand PostgreSQL database:
1. Runs init.sql to create database and extensions
2. Creates all tables using SQLAlchemy models
3. Validates connection and setup

Usage:
    python scripts/setup_database.py
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from dotenv import load_dotenv

from src.database.connection import get_engine, test_connection
from src.database.models import create_all_tables

# Load environment
load_dotenv()


def run_init_sql():
    """Run the init.sql file to create database and extensions"""
    print("📄 Running init.sql...")

    init_sql_path = Path(__file__).parent.parent / "database" / "init.sql"

    if not init_sql_path.exists():
        print(f"❌ init.sql not found at {init_sql_path}")
        return False

    # Get database connection parameters
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "westbrand")
    user = os.getenv("PGUSER", "WestBrandService")
    password = os.getenv("PGPASSWORD", "")

    # Build psql command
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    cmd = [
        "psql",
        "-h",
        host,
        "-p",
        port,
        "-U",
        user,
        "-d",
        database,
        "-f",
        str(init_sql_path),
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ init.sql executed successfully")
            return True
        else:
            print(f"❌ Error executing init.sql:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("⚠️  psql command not found - skipping init.sql")
        print("   Extensions may need to be created manually")
        return True  # Continue anyway
    except Exception as e:
        print(f"⚠️  Error running init.sql: {e}")
        print("   Continuing with table creation...")
        return True  # Continue anyway


def create_tables():
    """Create all database tables"""
    print("\n🏗️  Creating database tables...")

    try:
        engine = get_engine()
        create_all_tables(engine)
        print("✅ All tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def validate_setup():
    """Validate database connection and tables"""
    print("\n🔍 Validating database setup...")

    if not test_connection():
        print("❌ Database connection failed")
        return False

    print("✅ Database connection successful")

    # Test querying tables
    try:
        from sqlalchemy import text

        engine = get_engine()

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name IN (
                        'emails_processed',
                        'product_mentions',
                        'inventory_items',
                        'inventory_matches',
                        'match_review_flags'
                    )
                    ORDER BY table_name
                """)
            )
            tables = [row[0] for row in result]

        expected_tables = [
            "emails_processed",
            "inventory_items",
            "inventory_matches",
            "match_review_flags",
            "product_mentions",
        ]

        missing_tables = set(expected_tables) - set(tables)

        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False

        print(f"✅ All {len(expected_tables)} tables exist:")
        for table in expected_tables:
            print(f"   - {table}")

        return True

    except Exception as e:
        print(f"❌ Error validating setup: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("WestBrand Database Setup")
    print("=" * 60)

    # Check environment variables
    print("\n📋 Checking environment variables...")
    required_vars = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please check your .env file")
        sys.exit(1)

    print("✅ All required environment variables present")

    # Step 1: Run init.sql
    if not run_init_sql():
        print("\n⚠️  init.sql execution had issues, but continuing...")

    # Step 2: Create tables
    if not create_tables():
        print("\n❌ Setup failed: Could not create tables")
        sys.exit(1)

    # Step 3: Validate
    if not validate_setup():
        print("\n❌ Setup validation failed")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Database setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python scripts/import_inventory.py")
    print("2. Run: python scripts/import_existing_reports.py")
    print("3. Start analyzing new emails!")


if __name__ == "__main__":
    main()
