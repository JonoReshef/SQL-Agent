"""Unit tests for LLM-based product extraction"""

import pytest
from datetime import datetime
from src.llm.extractors import extract_products_from_email
from src.models.email import Email, EmailMetadata


class TestProductExtraction:
    """Test suite for LLM product extraction. NOTE this is using real LLM calls to verify end-to-end processing. It will be slower, possible non-deterministic and incur costs but is useful for verifying the full integration."""

    @pytest.mark.unit
    def test_extract_products_basic(self):
        """Test basic product extraction with mocked LLM"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="RFQ for Grade 8 Bolts",
                sender="customer@example.com",
                recipients=["sales@westbrand.ca"],
                date=datetime(2025, 1, 15, 10, 30),
            ),
            body='Please quote 100 pcs of 1/2-13 x 2" Grade 8 hex bolts, zinc plated.',
            cleaned_body='Please quote 100 pcs of 1/2-13 x 2" Grade 8 hex bolts, zinc plated.',
            file_path="test.msg",
        )

        products = extract_products_from_email(email)

        assert len(products) == 1
        assert products[0].product_name == "Hex Bolt"
        assert products[0].quantity == 100
        assert products[0].email_sender == "customer@example.com"

    @pytest.mark.unit
    def test_extract_products_multiple(self):
        """Test extraction of multiple products from one email"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Parts Request",
                sender="buyer@company.com",
                recipients=["sales@westbrand.ca"],
                date=None,
            ),
            body="Need 50 Grade 5 bolts and 200 washers",
            cleaned_body="Need 50 Grade 5 bolts and 200 washers",
            file_path="test2.msg",
        )

        products = extract_products_from_email(email)

        assert len(products) == 2
        assert products[0].quantity == 50
        assert products[1].quantity == 200

    @pytest.mark.unit
    def test_extract_products_no_products(self):
        """Test extraction when no products found"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Meeting Schedule",
                sender="admin@company.com",
                recipients=["team@westbrand.ca"],
                date=None,
            ),
            body="Let's schedule a meeting next week.",
            cleaned_body="Let's schedule a meeting next week.",
            file_path="test3.msg",
        )

        products = extract_products_from_email(email)

        assert len(products) == 0

    @pytest.mark.unit
    def test_extract_products_llm_error(self):
        """Test handling of LLM errors"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Test",
                sender="test@example.com",
                recipients=["sales@westbrand.ca"],
                date=None,
            ),
            body="Test body",
            cleaned_body="Test body",
            file_path="test4.msg",
        )

        products = extract_products_from_email(email)

        # Should return empty list on error, not raise
        assert len(products) == 0

    @pytest.mark.unit
    def test_extract_products_invalid_json(self):
        """Test handling of invalid JSON response"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Test",
                sender="test@example.com",
                recipients=["sales@westbrand.ca"],
                date=None,
            ),
            body="Test body",
            cleaned_body="Test body",
            file_path="test5.msg",
        )

        products = extract_products_from_email(email)

        # Should return empty list on parse error
        assert len(products) == 0

    @pytest.mark.unit
    def test_product_mention_metadata(self):
        """Test that email metadata is copied to product mentions"""
        email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Test Subject",
                sender="sender@example.com",
                recipients=["sales@westbrand.ca"],
                date=datetime(2025, 2, 1, 14, 30),
            ),
            body="Test",
            cleaned_body="Need 10 pcs of 1/2-13 hex bolts.",
            file_path="/path/to/test.msg",
        )

        products = extract_products_from_email(email)

        assert len(products) >= 1
        assert products[0].email_subject == "Test Subject"
        assert products[0].email_sender == "sender@example.com"
        assert products[0].email_file == "/path/to/test.msg"
        assert products[0].email_date == datetime(2025, 2, 1, 14, 30)
