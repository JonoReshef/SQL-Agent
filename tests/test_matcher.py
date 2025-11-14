"""Tests for matching system (normalizer and matcher)"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.matching.matcher import (
    calculate_match_score,
    find_best_matches,
    match_product_to_inventory,
)
from src.matching.normalizer import (
    batch_normalize_properties,
    calculate_property_similarity,
    find_matching_properties,
    normalize_property_value,
)

from src.models.inventory import InventoryItem
from src.models.product import ProductMention, ProductProperty

# Test Normalizer


def test_normalize_property_value_direct_match():
    """Test direct mapping normalization"""
    assert normalize_property_value("material", "ss") == "stainless steel"
    assert normalize_property_value("material", "zinc") == "zinc plated"
    assert normalize_property_value("grade", "gr8") == "8"
    assert normalize_property_value("grade", "grade 5") == "5"


def test_normalize_property_value_fuzzy_match():
    """Test fuzzy matching normalization"""
    # Close variations should match
    result = normalize_property_value("material", "stainless")  # close match
    assert result == "stainless steel"

    result = normalize_property_value("finish", "galvanized")  # exact match
    assert result == "galvanized"


def test_normalize_property_value_no_match():
    """Test that unknown values are returned cleaned"""
    result = normalize_property_value("color", "red")
    assert result == "red"

    result = normalize_property_value("unknown_prop", "some value")
    assert result == "some value"


def test_batch_normalize_properties():
    """Test batch normalization"""
    props = [
        ProductProperty(name="material", value="ss", confidence=0.9),
        ProductProperty(name="grade", value="gr8", confidence=0.95),
        ProductProperty(name="size", value="1/2-13", confidence=0.9),
    ]

    normalized = batch_normalize_properties(props)

    assert len(normalized) == 3
    assert normalized[0].value == "stainless steel"
    assert normalized[1].value == "8"
    assert normalized[2].value == "1/2-13"  # No normalization for size


def test_calculate_property_similarity_exact():
    """Test exact property match"""
    prop1 = ProductProperty(name="grade", value="8", confidence=0.9)
    prop2 = ProductProperty(name="grade", value="8", confidence=0.95)

    similarity = calculate_property_similarity(prop1, prop2)
    assert similarity == 1.0


def test_calculate_property_similarity_normalized():
    """Test property match with normalization"""
    prop1 = ProductProperty(name="material", value="ss", confidence=0.9)
    prop2 = ProductProperty(name="material", value="stainless steel", confidence=0.95)

    similarity = calculate_property_similarity(prop1, prop2, normalize=True)
    assert similarity == 1.0


def test_calculate_property_similarity_different_names():
    """Test that different property names return 0"""
    prop1 = ProductProperty(name="grade", value="8", confidence=0.9)
    prop2 = ProductProperty(name="size", value="8", confidence=0.9)

    similarity = calculate_property_similarity(prop1, prop2)
    assert similarity == 0.0


def test_find_matching_properties():
    """Test finding matching properties between lists"""
    source_props = [
        ProductProperty(name="grade", value="8", confidence=0.9),
        ProductProperty(name="size", value="1/2-13", confidence=0.9),
        ProductProperty(name="length", value="2 inches", confidence=0.85),
    ]

    target_props = [
        ProductProperty(name="grade", value="8", confidence=1.0),
        ProductProperty(name="size", value="1/2-13", confidence=1.0),
        ProductProperty(name="material", value="steel", confidence=1.0),
    ]

    matched, missing, scores = find_matching_properties(source_props, target_props)

    assert "grade" in matched
    assert "size" in matched
    assert "length" in missing  # Not in target
    assert len(scores) == 3


# Test Matcher


@pytest.fixture
def sample_product():
    """Sample product mention"""
    return ProductMention(
        exact_product_text="100 pcs of 1/2-13 Grade 8 hex bolts",
        product_name="Hex Bolt",
        product_category="Fasteners",
        properties=[
            ProductProperty(name="grade", value="8", confidence=0.95),
            ProductProperty(name="size", value="1/2-13", confidence=0.9),
        ],
        quantity=100,
        unit="pcs",
        context="quote_request",
        requestor="customer@example.com",
        date_requested="2025-02-15",
        email_subject="Request for bolts",
        email_sender="customer@example.com",
        email_file="email1.msg",
    )


@pytest.fixture
def sample_inventory():
    """Sample inventory items"""
    return [
        InventoryItem(
            item_number="BOLT-001",
            raw_description='1/2-13 x 2" Grade 8 Hex Bolt, Zinc Plated',
            exact_product_text='1/2-13 x 2" Grade 8 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
                ProductProperty(name="length", value='2"', confidence=1.0),
            ],
            parse_confidence=0.95,
            needs_manual_review=False,
        ),
        InventoryItem(
            item_number="BOLT-002",
            raw_description='3/4-10 x 3" Grade 5 Hex Bolt',
            exact_product_text='3/4-10 x 3" Grade 5 Hex Bolt',
            product_name="Hex Bolt",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="5", confidence=1.0),
                ProductProperty(name="size", value="3/4-10", confidence=1.0),
                ProductProperty(name="length", value='3"', confidence=1.0),
            ],
            parse_confidence=0.95,
            needs_manual_review=False,
        ),
        InventoryItem(
            item_number="NUT-001",
            raw_description="1/2-13 Lock Nut, Grade 8",
            exact_product_text="1/2-13 Lock Nut",
            product_name="Lock Nut",
            product_category="Fasteners",
            properties=[
                ProductProperty(name="grade", value="8", confidence=1.0),
                ProductProperty(name="size", value="1/2-13", confidence=1.0),
            ],
            parse_confidence=0.9,
            needs_manual_review=False,
        ),
    ]


def test_calculate_match_score(sample_product, sample_inventory):
    """Test match score calculation"""
    score, matched, missing, reasoning = calculate_match_score(
        sample_product, sample_inventory[0]
    )

    assert score > 0.7  # Should be a good match
    assert "grade" in matched
    assert "size" in matched
    assert isinstance(reasoning, str)
    assert len(reasoning) > 0


def test_find_best_matches(sample_product, sample_inventory):
    """Test finding best matches"""
    matches = find_best_matches(
        sample_product, sample_inventory, max_matches=3, min_score=0.5
    )

    assert len(matches) > 0
    assert len(matches) <= 3

    # Should be ranked
    assert matches[0].rank == 1
    if len(matches) > 1:
        assert matches[1].rank == 2
        # Scores should be descending
        assert matches[0].match_score >= matches[1].match_score

    # Top match should be BOLT-001 (same grade and size)
    assert matches[0].inventory_item_number == "BOLT-001"


def test_find_best_matches_no_matches(sample_product):
    """Test when no matches meet threshold"""
    # Product that doesn't match anything
    different_product = ProductMention(
        exact_product_text="M12 x 50mm stainless steel bolt",
        product_name="Metric Bolt",
        product_category="Fasteners",
        properties=[
            ProductProperty(name="size", value="M12", confidence=0.9),
            ProductProperty(name="length", value="50mm", confidence=0.9),
        ],
        quantity=50,
        unit="pcs",
        context="order",
        requestor="test@example.com",
        date_requested="2025-02-16",
        email_subject="Order",
        email_sender="test@example.com",
        email_file="test.msg",
    )

    # Very high threshold
    matches = find_best_matches(different_product, [], max_matches=3, min_score=0.9)

    assert len(matches) == 0


def test_match_product_to_inventory(sample_product, sample_inventory):
    """Test full product matching with review flags"""
    matches, flags = match_product_to_inventory(
        sample_product,
        sample_inventory,
        max_matches=3,
        min_score=0.5,
        review_threshold=0.7,
    )

    assert len(matches) > 0
    assert isinstance(flags, list)

    # Top match should be BOLT-001
    assert matches[0].inventory_item_number == "BOLT-001"


def test_match_product_to_inventory_no_matches(sample_product):
    """Test review flag when no matches found"""
    matches, flags = match_product_to_inventory(
        sample_product, [], max_matches=3, min_score=0.5, review_threshold=0.7
    )

    assert len(matches) == 0
    assert len(flags) > 0
    assert flags[0].issue_type == "INSUFFICIENT_DATA"


def test_match_product_to_inventory_low_confidence(sample_product, sample_inventory):
    """Test review flag for low confidence match"""
    matches, flags = match_product_to_inventory(
        sample_product,
        sample_inventory,
        max_matches=3,
        min_score=0.3,  # Low threshold
        review_threshold=0.95,  # High review threshold
    )

    # Should find matches but flag for review
    assert len(matches) > 0

    # Check if low confidence flag is present
    low_conf_flags = [f for f in flags if f.issue_type == "LOW_CONFIDENCE"]
    assert len(low_conf_flags) > 0 or matches[0].match_score >= 0.95


@pytest.mark.unit
def test_edge_case_empty_properties():
    """Test matching with empty properties"""
    product = ProductMention(
        exact_product_text="Some product",
        product_name="Product",
        product_category="Category",
        properties=[],
        context="other",
        email_subject="Test",
        email_sender="test@example.com",
        email_file=None,
    )

    inv_item = InventoryItem(
        item_number="ITEM-001",
        raw_description="Some inventory item",
        exact_product_text="Some item",
        product_name="Product",
        product_category="Category",
        properties=[],
    )

    score, matched, missing, reasoning = calculate_match_score(product, inv_item)

    assert score >= 0.0
    assert score <= 1.0
    assert len(matched) == 0
    assert len(missing) == 0
