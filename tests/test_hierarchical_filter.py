"""Tests for hierarchical filtering logic"""

import pytest

from src.matching.filter import (
    filter_by_property,
    hierarchical_filter,
    score_filtered_items,
)
from src.matching.hierarchy import PropertyHierarchy
from src.models.inventory import InventoryItem
from src.models.product import ProductMention, ProductProperty


@pytest.fixture
def fastener_hierarchy():
    """Fasteners property hierarchy"""
    return PropertyHierarchy(
        category="Fasteners",
        property_order=["grade", "size", "length", "material", "finish"],
    )


@pytest.fixture
def sample_fastener_inventory():
    """Sample inventory of fasteners with various properties"""
    return [
        # Grade 8, size 1/2-13
        InventoryItem(
            item_number="BOLT-001",
            raw_description='1/2-13 x 2" Grade 8 Hex Bolt, Zinc',
            exact_product_text='1/2-13 x 2" Grade 8 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
                ProductProperty(name="length", value='2"', confidence=1.0),
                ProductProperty(name="finish", value="zinc", confidence=1.0),
            ],
        ),
        # Grade 8, size 1/2-13, different length
        InventoryItem(
            item_number="BOLT-002",
            raw_description='1/2-13 x 3" Grade 8 Hex Bolt',
            exact_product_text='1/2-13 x 3" Grade 8 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
                ProductProperty(name="length", value='3"', confidence=1.0),
            ],
        ),
        # Grade 8, different size
        InventoryItem(
            item_number="BOLT-003",
            raw_description='3/4-10 x 2" Grade 8 Hex Bolt',
            exact_product_text='3/4-10 x 2" Grade 8 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="3/4-10", confidence=1.0),
                ProductProperty(name="length", value='2"', confidence=1.0),
            ],
        ),
        # Grade 5, size 1/2-13
        InventoryItem(
            item_number="BOLT-004",
            raw_description='1/2-13 x 2" Grade 5 Hex Bolt',
            exact_product_text='1/2-13 x 2" Grade 5 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="5", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
                ProductProperty(name="length", value='2"', confidence=1.0),
            ],
        ),
        # Grade 8, size 1/2-13, no length specified
        InventoryItem(
            item_number="BOLT-005",
            raw_description="1/2-13 Grade 8 Hex Bolt",
            exact_product_text="1/2-13 Grade 8 Hex Bolt",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
            ],
        ),
    ]


class TestFilterByProperty:
    """Test single-property filtering"""

    def test_filter_exact_match(self, sample_fastener_inventory):
        """Test filtering with exact property match"""
        target_property = ProductProperty(name="grade", value="8", confidence=0.9)

        filtered = filter_by_property(
            sample_fastener_inventory,
            target_property,
            min_similarity=0.9,  # Exact match required
        )

        # Should get 4 items with grade 8 (BOLT-001, 002, 003, 005)
        assert len(filtered) == 4
        assert all(
            any(p.name == "grade" and p.value == "8" for p in item.properties)
            for item in filtered
        )

    def test_filter_fuzzy_match(self, sample_fastener_inventory):
        """Test filtering with fuzzy matching"""
        # Use normalized material value
        target_property = ProductProperty(
            name="material", value="stainless steel", confidence=0.9
        )

        # Add item with fuzzy match
        sample_fastener_inventory.append(
            InventoryItem(
                item_number="BOLT-SS",
                raw_description="1/2-13 Grade 8 SS Hex Bolt",
                exact_product_text="1/2-13 Grade 8 SS Hex Bolt",
                product_name="Hex Bolt",
                product_category="Fasteners",
                properties=[
                    ProductProperty(name="grade", value="8", confidence=1.0),
                    ProductProperty(name="material", value="ss", confidence=1.0),
                ],
            )
        )

        filtered = filter_by_property(
            sample_fastener_inventory,
            target_property,
            min_similarity=0.8,  # Allow fuzzy match
        )

        # Should find the SS item (normalized to stainless steel)
        assert len(filtered) >= 1
        assert any(item.item_number == "BOLT-SS" for item in filtered)

    def test_filter_no_matches(self, sample_fastener_inventory):
        """Test filtering when no items match"""
        target_property = ProductProperty(name="grade", value="B7", confidence=0.9)

        filtered = filter_by_property(
            sample_fastener_inventory, target_property, min_similarity=0.9
        )

        # Should get no matches (no B7 in inventory)
        assert len(filtered) == 0

    def test_filter_property_not_present(self, sample_fastener_inventory):
        """Test filtering by property that some items don't have"""
        target_property = ProductProperty(name="length", value='2"', confidence=0.9)

        filtered = filter_by_property(
            sample_fastener_inventory, target_property, min_similarity=0.9
        )

        # Should only get items with length=2" (BOLT-001, 003, 004)
        assert len(filtered) == 3
        assert all(
            any(p.name == "length" and p.value == '2"' for p in item.properties)
            for item in filtered
        )


class TestHierarchicalFilter:
    """Test hierarchical filtering algorithm"""

    def test_single_level_hierarchy(
        self, sample_fastener_inventory, fastener_hierarchy
    ):
        """Test filtering with product that has only one property"""
        product = ProductMention(
            exact_product_text="Grade 8 bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should filter to grade 8 items only
        assert len(filtered) == 4  # BOLT-001, 002, 003, 005

    def test_two_level_hierarchy(self, sample_fastener_inventory, fastener_hierarchy):
        """Test filtering with two properties in hierarchy"""
        product = ProductMention(
            exact_product_text="1/2-13 Grade 8 bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
                ProductProperty(name="size", value="1/2-13", confidence=0.9),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should filter to grade 8, size 1/2-13 (BOLT-001, 002, 005)
        assert len(filtered) == 3
        item_numbers = {item.item_number for item in filtered}
        assert item_numbers == {"BOLT-001", "BOLT-002", "BOLT-005"}

    def test_three_level_hierarchy(self, sample_fastener_inventory, fastener_hierarchy):
        """Test filtering with three properties in hierarchy"""
        product = ProductMention(
            exact_product_text='1/2-13 x 2" Grade 8 bolts',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
                ProductProperty(name="size", value="1/2-13", confidence=0.9),
                ProductProperty(name="length", value='2"', confidence=0.85),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should filter to grade 8, size 1/2-13, length 2" (BOLT-001 only)
        assert len(filtered) == 1
        assert filtered[0].item_number == "BOLT-001"

    def test_hierarchy_with_missing_inventory_property(
        self, sample_fastener_inventory, fastener_hierarchy
    ):
        """Test that items without a hierarchical property are still included if they match earlier levels"""
        product = ProductMention(
            exact_product_text='1/2-13 x 4" Grade 8 bolts',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
                ProductProperty(name="size", value="1/2-13", confidence=0.9),
                ProductProperty(
                    name="length", value='4"', confidence=0.85
                ),  # Not in any inventory
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should still return items that match grade and size, even if length doesn't match
        # Including BOLT-005 which has no length property
        assert len(filtered) >= 1
        item_numbers = {item.item_number for item in filtered}
        assert "BOLT-005" in item_numbers  # Item without length should be included

    def test_properties_out_of_hierarchy_order(
        self, sample_fastener_inventory, fastener_hierarchy
    ):
        """Test that product properties are processed in hierarchy order, not product order"""
        product = ProductMention(
            exact_product_text='2" Grade 8 1/2-13 bolts',  # Properties listed out of order
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(
                    name="length", value='2"', confidence=0.85
                ),  # Listed first
                ProductProperty(name="grade", value="8", confidence=0.95),
                ProductProperty(name="size", value="1/2-13", confidence=0.9),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should process in hierarchy order: grade -> size -> length
        # Result should be same as if properties were in order
        assert len(filtered) == 1
        assert filtered[0].item_number == "BOLT-001"

    def test_empty_inventory(self, fastener_hierarchy):
        """Test hierarchical filter with empty inventory"""
        product = ProductMention(
            exact_product_text="Grade 8 bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(product, [], fastener_hierarchy)

        assert len(filtered) == 0

    def test_product_with_no_properties(
        self, sample_fastener_inventory, fastener_hierarchy
    ):
        """Test product with no properties returns all inventory"""
        product = ProductMention(
            exact_product_text="bolts",
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[],  # No properties
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        filtered = hierarchical_filter(
            product, sample_fastener_inventory, fastener_hierarchy
        )

        # Should return all items (no filtering)
        assert len(filtered) == len(sample_fastener_inventory)


class TestScoreFilteredItems:
    """Test scoring of hierarchically filtered items"""

    def test_score_exact_matches_higher(
        self, sample_fastener_inventory, fastener_hierarchy
    ):
        """Test that items matching more hierarchy levels score higher"""
        product = ProductMention(
            exact_product_text='1/2-13 x 2" Grade 8 bolts',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=0.95),
                ProductProperty(name="size", value="1/2-13", confidence=0.9),
                ProductProperty(name="length", value='2"', confidence=0.85),
            ],
            quantity=100,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_file="test.msg",
            thread_hash="abc123",
        )

        # Filter to grade 8, size 1/2-13
        candidates = [
            item
            for item in sample_fastener_inventory
            if any(p.name == "grade" and p.value == "8" for p in item.properties)
            and any(p.name == "size" and p.value == "1/2-13" for p in item.properties)
        ]

        scored = score_filtered_items(product, candidates, fastener_hierarchy)

        # BOLT-001 (matches all 3: grade, size, length) should score highest
        assert len(scored) > 0
        assert scored[0][0].item_number == "BOLT-001"

        # Items matching fewer properties should score lower
        scores = [score for _, score in scored]
        assert scores[0] > scores[-1]  # First score > last score
