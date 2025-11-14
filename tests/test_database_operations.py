"""Tests for database operations"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime

import pytest
from sqlalchemy import delete, select

from src.database.connection import get_db_session, test_connection
from src.database.models import (
    EmailProcessed,
    InventoryItem,
    InventoryMatch,
    MatchReviewFlag,
    ProductMention,
)
from src.database.operations import (
    sanitize_for_db,
    store_emails,
    store_inventory_matches,
    store_product_mentions,
    store_review_flags,
)
from src.models.email import Email, EmailMetadata
from src.models.inventory import (
    InventoryMatch as PydanticInventoryMatch,
)
from src.models.inventory import (
    ReviewFlag,
)
from src.models.product import ProductMention as PydanticProductMention
from src.models.product import ProductProperty


@pytest.fixture
def sample_email():
    """Create a sample email for testing"""
    return Email(
        metadata=EmailMetadata(
            message_id="test@example.com",
            subject="Test Email",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            cc=[],
            date=datetime(2025, 1, 1, 12, 0, 0),
        ),
        body="Test email body",
        cleaned_body="Test email body",
        attachments=[],
        file_path="test_email.msg",
    )


@pytest.fixture
def sample_product(sample_email):
    """Create a sample product mention"""
    return PydanticProductMention(
        exact_product_text="1/2-13 x 2 inch Grade 8 Hex Bolt",
        product_name="Hex Bolt",
        product_category="Fasteners",
        properties=[
            ProductProperty(name="grade", value="8", confidence=0.95),
            ProductProperty(name="size", value="1/2-13", confidence=0.90),
        ],
        quantity=100,
        unit="pcs",
        context="Customer order",
        requestor="John Doe",
        date_requested="2025-01-01",
        email_subject=sample_email.metadata.subject,
        email_sender=sample_email.metadata.sender,
        email_file=sample_email.file_path,
    )


@pytest.fixture
def cleanup_test_data():
    """Cleanup test data after each test"""
    yield
    # Cleanup after test
    with get_db_session() as session:
        # Delete in order of dependencies
        session.execute(delete(MatchReviewFlag))
        session.execute(delete(InventoryMatch))
        session.execute(delete(ProductMention))
        session.execute(
            delete(EmailProcessed).where(EmailProcessed.file_path == "test_email.msg")
        )
        session.execute(
            delete(InventoryItem).where(InventoryItem.item_number.like("TEST%"))
        )
        session.commit()


@pytest.mark.integration
def test_database_connection():
    """Test database connection is working"""
    assert test_connection() is True


@pytest.mark.integration
def test_sanitize_for_db():
    """Test NUL byte sanitization"""
    # Test with NUL bytes
    text_with_nul = "Test\x00String"
    assert sanitize_for_db(text_with_nul) == "TestString"

    # Test with None
    assert sanitize_for_db(None) is None

    # Test with normal string
    assert sanitize_for_db("Normal String") == "Normal String"


@pytest.mark.integration
def test_store_emails(sample_email, cleanup_test_data):
    """Test storing emails to database"""
    result = store_emails([sample_email])

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["errors"] == 0

    # Verify in database
    with get_db_session() as session:
        stmt = select(EmailProcessed).where(
            EmailProcessed.file_path == sample_email.file_path
        )
        db_email = session.execute(stmt).scalar_one()

        assert db_email.subject == sample_email.metadata.subject
        assert db_email.sender == sample_email.metadata.sender

    # Test update
    result = store_emails([sample_email])
    assert result["inserted"] == 0
    assert result["updated"] == 1


@pytest.mark.integration
def test_store_product_mentions(sample_email, sample_product, cleanup_test_data):
    """Test storing product mentions to database"""
    # First store the email
    store_emails([sample_email])

    # Then store products
    result = store_product_mentions([sample_product], [sample_email])

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["errors"] == 0

    # Verify in database
    with get_db_session() as session:
        stmt = select(ProductMention)
        db_product = session.execute(stmt).scalar_one()

        assert db_product.product_name == sample_product.product_name
        assert db_product.product_category == sample_product.product_category
        assert len(db_product.properties) == 2


@pytest.mark.integration
def test_store_inventory_matches(sample_email, sample_product, cleanup_test_data):
    """Test storing inventory matches to database"""
    # Setup: store email, product, and inventory item
    store_emails([sample_email])
    store_product_mentions([sample_product], [sample_email])

    # Create test inventory item
    with get_db_session() as session:
        inventory_item = InventoryItem(
            item_number="TEST-001",
            raw_description="1/2-13 x 2 inch Grade 8 Hex Bolt",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                {"name": "grade", "value": "8", "confidence": 0.95},
                {"name": "size", "value": "1/2-13", "confidence": 0.90},
            ],
        )
        session.add(inventory_item)
        session.commit()

    # Create match
    match = PydanticInventoryMatch(
        inventory_item_number="TEST-001",
        inventory_description="1/2-13 x 2 inch Grade 8 Hex Bolt",
        match_score=0.95,
        rank=1,
        matched_properties=["grade", "size"],
        missing_properties=[],
        match_reasoning="Exact match on all properties",
    )

    product_matches = {sample_product.exact_product_text: [match]}

    result = store_inventory_matches(product_matches, [sample_product])

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["errors"] == 0

    # Verify in database
    with get_db_session() as session:
        stmt = select(InventoryMatch)
        db_match = session.execute(stmt).scalar_one()

        assert db_match.match_score == 0.95
        assert db_match.rank == 1


@pytest.mark.integration
def test_store_review_flags(sample_email, sample_product, cleanup_test_data):
    """Test storing review flags to database"""
    # Setup: store email and product
    store_emails([sample_email])
    store_product_mentions([sample_product], [sample_email])

    # Create flag
    flag = ReviewFlag(
        product_text=sample_product.exact_product_text,
        product_name=sample_product.product_name,
        product_category=sample_product.product_category,
        issue_type="LOW_CONFIDENCE",
        match_count=1,
        top_confidence=0.65,
        reason="Match score below threshold",
        action_needed="Manual review recommended",
    )

    result = store_review_flags([flag], [sample_product])

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["errors"] == 0

    # Verify in database
    with get_db_session() as session:
        stmt = select(MatchReviewFlag)
        db_flag = session.execute(stmt).scalar_one()

        assert db_flag.issue_type == "LOW_CONFIDENCE"
        assert db_flag.match_count == 1
        assert db_flag.top_confidence == 0.65


@pytest.mark.integration
def test_full_workflow_with_database():
    """Test complete workflow stores data to database correctly"""
    from pathlib import Path

    from src.workflow.graph import run_workflow

    # Use test fixtures
    test_input = "data/selected"
    test_output = "output/test_integration_db.xlsx"

    if not Path(test_input).exists():
        pytest.skip("Test data directory not available")

    # Run workflow without matching
    final_state = run_workflow(test_input, test_output, enable_matching=False)

    # Verify data was stored
    with get_db_session() as session:
        email_count = session.execute(
            select(EmailProcessed).where(
                EmailProcessed.file_path.like(f"{test_input}%")
            )
        ).all()
        product_count = session.execute(select(ProductMention)).all()

        assert len(email_count) > 0
        assert len(product_count) > 0

    # Cleanup
    Path(test_output).unlink(missing_ok=True)
