"""Unit tests for LLM-based product extraction"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from analysis_workflow.nodes.extraction.extractors import (
    deduplicate_ai_product_mentions,
    extract_products_from_email,
)

from workflow.models.email import Email, EmailMetadata
from workflow.models.product import ProductMention, ProductProperty


class TestProductExtraction:
    """Test suite for LLM product extraction. This uses mocking to simulate LLM responses and is suitable for testing the extraction logic without incurring LLM costs."""

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

        # Mock LLM response
        mock_response = {
            "products": [
                {
                    "product_name": "Hex Bolt",
                    "product_category": "Fasteners",
                    "properties": {
                        "grade": "8",
                        "size": "1/2-13",
                        "length": '2"',
                        "finish": "zinc plated",
                    },
                    "quantity": 100,
                    "unit": "pcs",
                    "context": "quote_request",
                }
            ]
        }

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = json.dumps(mock_response)
            mock_get_client.return_value = mock_llm

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

        mock_response = {
            "products": [
                {
                    "product_name": "Bolt",
                    "product_category": "Fasteners",
                    "properties": {"grade": "5"},
                    "quantity": 50,
                    "unit": "pcs",
                    "context": "request",
                },
                {
                    "product_name": "Washer",
                    "product_category": "Washers",
                    "properties": {},
                    "quantity": 200,
                    "unit": "pcs",
                    "context": "request",
                },
            ]
        }

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = json.dumps(mock_response)
            mock_get_client.return_value = mock_llm

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

        mock_response = {"products": []}

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = json.dumps(mock_response)
            mock_get_client.return_value = mock_llm

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

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_llm

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

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "Not valid JSON"
            mock_get_client.return_value = mock_llm

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
            cleaned_body="Test",
            file_path="/path/to/test.msg",
        )

        mock_response = {
            "products": [
                {
                    "product_name": "Test Product",
                    "product_category": "Test",
                    "properties": {},
                    "quantity": 10,
                    "unit": "pcs",
                    "context": "test",
                }
            ]
        }

        with patch("src.llm.extractors.get_llm_client") as mock_get_client:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = json.dumps(mock_response)
            mock_get_client.return_value = mock_llm

            products = extract_products_from_email(email)

            assert len(products) == 1
            assert products[0].email_subject == "Test Subject"
            assert products[0].email_sender == "sender@example.com"
            assert products[0].email_file == "/path/to/test.msg"


class TestProductExtractionWithLLM:
    """Test suite for LLM product extraction. NOTE this is using real LLM calls to verify end-to-end processing. It will be slower, possible non-deterministic and incur costs but is useful for verifying the full integration. Use this test specifically to evaluate that AI responses are generated and handled correctly."""

    @pytest.mark.ai
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

    @pytest.mark.ai
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

    @pytest.mark.ai
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

    @pytest.mark.ai
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

    @pytest.mark.ai
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

    @pytest.mark.ai
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


class TestDeduplication:
    """Test suite for product mention deduplication"""

    def test_deduplicate_identical_products(self):
        """Test that identical products are deduplicated"""
        products = [
            ProductMention(
                exact_product_text="Viton O-rings, orange color, 1 inch size, 150LB pressure rating, ASME B16.21 standard",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                    ProductProperty(name="color", value="orange", confidence=1.0),
                    ProductProperty(name="size", value='1"', confidence=1.0),
                    ProductProperty(
                        name="pressure_rating", value="150LB", confidence=1.0
                    ),
                    ProductProperty(
                        name="standard", value="ASME B16.21", confidence=1.0
                    ),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested="2025-01-15",
                email_subject="RFQ for O-rings",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
            ProductMention(
                exact_product_text="Viton O-rings, orange color, 1 inch size, 150LB pressure rating, ASME B16.21 standard",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                    ProductProperty(name="color", value="orange", confidence=1.0),
                    ProductProperty(name="size", value='1"', confidence=1.0),
                    ProductProperty(
                        name="pressure_rating", value="150LB", confidence=1.0
                    ),
                    ProductProperty(
                        name="standard", value="ASME B16.21", confidence=1.0
                    ),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested="2025-01-15",
                email_subject="RFQ for O-rings",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
        ]

        deduplicated = deduplicate_ai_product_mentions(products)

        assert len(deduplicated) == 1
        assert deduplicated[0].product_name == "O-Ring"
        assert deduplicated[0].quantity == 50

    def test_deduplicate_different_quantities_kept(self):
        """Test that products with different quantities are kept separate"""
        products = [
            ProductMention(
                exact_product_text="Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested=None,
                email_subject="RFQ",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
            ProductMention(
                exact_product_text="Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                ],
                quantity=100,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested=None,
                email_subject="RFQ",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
        ]

        deduplicated = deduplicate_ai_product_mentions(products)

        assert len(deduplicated) == 2

    def test_deduplicate_different_properties_kept(self):
        """Test that products with different properties are kept separate"""
        products = [
            ProductMention(
                exact_product_text="Orange Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                    ProductProperty(name="color", value="orange", confidence=1.0),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested=None,
                email_subject="RFQ",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
            ProductMention(
                exact_product_text="Black Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                    ProductProperty(name="color", value="black", confidence=1.0),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested=None,
                email_subject="RFQ",
                email_sender="sophia@sealsring.cn",
                email_file="test.msg",
            ),
        ]

        deduplicated = deduplicate_ai_product_mentions(products)

        assert len(deduplicated) == 2

    def test_deduplicate_different_requestors_kept(self):
        """Test that products from different requestors are kept separate"""
        products = [
            ProductMention(
                exact_product_text="Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="sophia@sealsring.cn",
                date_requested=None,
                email_subject="RFQ",
                email_sender="sophia@sealsring.cn",
                email_file="test1.msg",
            ),
            ProductMention(
                exact_product_text="Viton O-rings",
                product_name="O-Ring",
                product_category="Seals",
                properties=[
                    ProductProperty(name="material", value="Viton", confidence=1.0),
                ],
                quantity=50,
                unit="pcs",
                context="quote_request",
                requestor="john@company.com",
                date_requested=None,
                email_subject="RFQ",
                email_sender="john@company.com",
                email_file="test2.msg",
            ),
        ]

        deduplicated = deduplicate_ai_product_mentions(products)

        assert len(deduplicated) == 2

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list"""
        products = []
        deduplicated = deduplicate_ai_product_mentions(products)
        assert len(deduplicated) == 0
