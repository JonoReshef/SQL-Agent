"""Unit tests for database connection and models"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_db_session, get_engine, test_connection
from src.database.models import (
    EmailProcessed,
    InventoryItem,
    InventoryMatch,
    MatchReviewFlag,
    ProductMention,
    create_all_tables,
    drop_all_tables,
)


@pytest.fixture
def test_engine():
    """Create a test database engine"""
    engine = get_engine(echo=False)

    # Create all tables
    create_all_tables(engine)

    yield engine

    # Cleanup: drop all tables
    drop_all_tables(engine)
    engine.dispose()


@pytest.mark.unit
def test_database_connection():
    """Test that we can connect to the database"""
    assert test_connection(), "Database connection should succeed"


@pytest.mark.unit
def test_create_tables(test_engine):
    """Test that all tables can be created"""
    # Tables should already be created by fixture
    with test_engine.connect() as conn:
        # Check that tables exist
        result = conn.execute(
            text(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                """
            )
        )
        tables = [row[0] for row in result]

        assert "emails_processed" in tables
        assert "product_mentions" in tables
        assert "inventory_items" in tables
        assert "inventory_matches" in tables
        assert "match_review_flags" in tables


@pytest.mark.unit
def test_email_processed_model(test_engine):
    """Test EmailProcessed model CRUD operations"""
    with get_db_session(test_engine) as session:
        # Create
        email = EmailProcessed(
            file_path="/test/email.msg",
            file_hash="abc123",
            subject="Test Email",
            sender="test@example.com",
            date_sent=datetime(2025, 1, 1, 10, 0),
        )
        session.add(email)
        session.commit()

        # Read
        retrieved = session.query(EmailProcessed).filter_by(file_hash="abc123").first()
        assert retrieved is not None
        assert retrieved.subject == "Test Email"
        assert retrieved.sender == "test@example.com"

        # Update
        retrieved.report_file = "/output/report.xlsx"
        session.commit()

        updated = session.query(EmailProcessed).filter_by(file_hash="abc123").first()
        assert updated.report_file == "/output/report.xlsx"

        # Delete
        session.delete(updated)
        session.commit()

        deleted = session.query(EmailProcessed).filter_by(file_hash="abc123").first()
        assert deleted is None


@pytest.mark.unit
def test_product_mention_model(test_engine):
    """Test ProductMention model with relationships"""
    with get_db_session(test_engine) as session:
        # Create email first
        email = EmailProcessed(
            file_path="/test/email.msg",
            file_hash="xyz789",
            subject="Product Request",
            sender="customer@example.com",
        )
        session.add(email)
        session.flush()

        # Create product mention
        product = ProductMention(
            email_id=email.id,
            exact_product_text="100 pcs of 1/2-13 Grade 8 bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                {"name": "grade", "value": "8", "confidence": 0.95},
                {"name": "size", "value": "1/2-13", "confidence": 0.90},
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            extraction_confidence=0.92,
        )
        session.add(product)
        session.commit()

        # Query with relationship
        retrieved_email = (
            session.query(EmailProcessed).filter_by(file_hash="xyz789").first()
        )
        assert len(retrieved_email.product_mentions) == 1
        assert retrieved_email.product_mentions[0].product_name == "Hex Bolt"
        assert len(retrieved_email.product_mentions[0].properties) == 2


@pytest.mark.unit
def test_inventory_item_model(test_engine):
    """Test InventoryItem model"""
    with get_db_session(test_engine) as session:
        item = InventoryItem(
            item_number="ITEM-001",
            raw_description='1/2-13 x 2" Grade 8 Hex Bolt, Zinc Plated',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                {"name": "grade", "value": "8", "confidence": 0.95},
                {"name": "size", "value": "1/2-13", "confidence": 0.90},
                {"name": "length", "value": '2"', "confidence": 0.85},
            ],
            parse_confidence=0.90,
            needs_manual_review=False,
        )
        session.add(item)
        session.commit()

        retrieved = (
            session.query(InventoryItem).filter_by(item_number="ITEM-001").first()
        )
        assert retrieved is not None
        assert retrieved.product_category == "Fasteners"
        assert len(retrieved.properties) == 3
        assert not retrieved.needs_manual_review


@pytest.mark.unit
def test_inventory_match_model(test_engine):
    """Test InventoryMatch with full relationships"""
    with get_db_session(test_engine) as session:
        # Create email
        email = EmailProcessed(
            file_path="/test/match_email.msg",
            file_hash="match123",
            subject="Match Test",
            sender="test@example.com",
        )
        session.add(email)
        session.flush()

        # Create product mention
        product = ProductMention(
            email_id=email.id,
            exact_product_text="Grade 8 bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[{"name": "grade", "value": "8", "confidence": 0.95}],
        )
        session.add(product)
        session.flush()

        # Create inventory item
        inventory = InventoryItem(
            item_number="BOLT-001",
            raw_description="1/2-13 Grade 8 Hex Bolt",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                {"name": "grade", "value": "8", "confidence": 0.95},
                {"name": "size", "value": "1/2-13", "confidence": 0.90},
            ],
        )
        session.add(inventory)
        session.flush()

        # Create match
        match = InventoryMatch(
            product_mention_id=product.id,
            inventory_item_id=inventory.id,
            match_score=0.85,
            rank=1,
            matched_properties=["grade"],
            missing_properties=["size"],
            match_reasoning="Grade matches exactly, but size not specified in email",
        )
        session.add(match)
        session.commit()

        # Query relationships
        retrieved_product = (
            session.query(ProductMention).filter_by(id=product.id).first()
        )
        assert len(retrieved_product.inventory_matches) == 1
        assert retrieved_product.inventory_matches[0].match_score == 0.85
        assert (
            retrieved_product.inventory_matches[0].inventory_item.item_number
            == "BOLT-001"
        )


@pytest.mark.unit
def test_match_review_flag_model(test_engine):
    """Test MatchReviewFlag model"""
    with get_db_session(test_engine) as session:
        # Create email and product
        email = EmailProcessed(
            file_path="/test/flag_email.msg",
            file_hash="flag123",
            subject="Flag Test",
        )
        session.add(email)
        session.flush()

        product = ProductMention(
            email_id=email.id,
            exact_product_text="Bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[],
        )
        session.add(product)
        session.flush()

        # Create review flag
        flag = MatchReviewFlag(
            product_mention_id=product.id,
            issue_type="INSUFFICIENT_DATA",
            match_count=0,
            top_confidence=None,
            reason="No properties specified - cannot determine specific bolt type",
            action_needed="Request more details from customer",
            is_resolved=False,
        )
        session.add(flag)
        session.commit()

        # Query
        retrieved = (
            session.query(MatchReviewFlag)
            .filter_by(product_mention_id=product.id)
            .first()
        )
        assert retrieved is not None
        assert retrieved.issue_type == "INSUFFICIENT_DATA"
        assert not retrieved.is_resolved
        assert retrieved.action_needed == "Request more details from customer"


@pytest.mark.unit
def test_cascade_delete(test_engine):
    """Test that cascading deletes work properly"""
    with get_db_session(test_engine) as session:
        # Create email with product mention
        email = EmailProcessed(
            file_path="/test/cascade_email.msg",
            file_hash="cascade123",
            subject="Cascade Test",
        )
        session.add(email)
        session.flush()

        product = ProductMention(
            email_id=email.id,
            exact_product_text="Test product",
            product_name="Test",
            product_category="Test",
            properties=[],
        )
        session.add(product)
        session.commit()

        product_id = product.id

        # Delete email - should cascade to product mention
        session.delete(email)
        session.commit()

        # Product mention should be deleted
        deleted_product = session.query(ProductMention).filter_by(id=product_id).first()
        assert deleted_product is None


@pytest.mark.unit
def test_unique_constraints(test_engine):
    """Test unique constraints on models"""
    with get_db_session(test_engine) as session:
        # Create inventory item
        item1 = InventoryItem(
            item_number="UNIQUE-001",
            raw_description="Test item",
            product_name="Test",
            product_category="Test",
            properties=[],
        )
        session.add(item1)
        session.commit()

    # Try to create duplicate item_number in new session
    with pytest.raises(Exception):  # Should raise IntegrityError
        with get_db_session(test_engine) as session:
            item2 = InventoryItem(
                item_number="UNIQUE-001",
                raw_description="Different description",
                product_name="Test2",
                product_category="Test",
                properties=[],
            )
            session.add(item2)
            session.commit()
