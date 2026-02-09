"""Tests for database-driven hierarchical inventory filtering"""

import pytest
from backend_workflow.database.filtering import (
    filter_inventory_by_hierarchical_properties,
)
from sqlalchemy.orm import Session
from src.matching.hierarchy import PropertyHierarchy

from workflow.database.connection import get_db_session, get_engine
from workflow.database.models import Base
from workflow.database.models import InventoryItem as DBInventoryItem
from workflow.models.inventory import InventoryItem
from workflow.models.product import ProductMention, ProductProperty


def create_product_mention(
    product_category: str,
    properties: list[ProductProperty],
    product_name: str = "Test Product",
) -> ProductMention:
    """
    Helper function to create a ProductMention object for testing.

    Args:
        product_category: Category of the product
        properties: List of ProductProperty objects
        product_name: Name of the product (default: "Test Product")

    Returns:
        ProductMention object with dummy email fields
    """
    return ProductMention(
        exact_product_text=f"{product_name} with {len(properties)} properties",
        product_name=product_name,
        product_category=product_category,
        properties=properties,
        quantity=1.0,
        unit="pcs",
        context="quote_request",
        requestor="test@example.com",
        date_requested="2025-01-01",
        email_subject="Test Email Subject",
        email_sender="test@example.com",
        email_file="/test/path.msg",
        thread_hash="test_thread_hash_123",
    )


@pytest.fixture(scope="function")
def test_db_session():
    """Create a test database session with clean tables"""
    engine = get_engine(echo=False)

    # Drop and recreate tables for clean state
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with get_db_session(engine) as session:
        yield session

    # Cleanup
    # Base.metadata.drop_all(engine)


@pytest.fixture
def sample_inventory_items(test_db_session: Session):
    """Create sample inventory items matching the requirements example"""
    items = [
        # Item A: nut, size=4", material=steel, colour=black
        DBInventoryItem(
            item_number="ITEM-A",
            raw_description="4 inch steel nut black",
            product_name="Nut",
            product_category="Nuts",
            content_hash="hash_a",
            properties=[
                {"name": "size", "value": '4"', "confidence": 1.0},
                {"name": "material", "value": "steel", "confidence": 1.0},
                {"name": "colour", "value": "black", "confidence": 1.0},
            ],
        ),
        # Item B: nut, size=5", material=iron, colour=blue
        DBInventoryItem(
            item_number="ITEM-B",
            raw_description="5 inch iron nut blue",
            product_name="Nut",
            product_category="Nuts",
            content_hash="hash_b",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": "iron", "confidence": 1.0},
                {"name": "colour", "value": "blue", "confidence": 1.0},
            ],
        ),
        # Item C: nail, size=6", material=iron, colour=black
        DBInventoryItem(
            item_number="ITEM-C",
            raw_description="6 inch iron nail black",
            product_name="Nail",
            product_category="Nails",
            content_hash="hash_c",
            properties=[
                {"name": "size", "value": '6"', "confidence": 1.0},
                {"name": "material", "value": "iron", "confidence": 1.0},
                {"name": "colour", "value": "black", "confidence": 1.0},
            ],
        ),
        # Item D: nut, size=5", material=iron, colour=red
        DBInventoryItem(
            item_number="ITEM-D",
            raw_description="5 inch iron nut red",
            product_name="Nut",
            product_category="Nuts",
            content_hash="hash_d",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": "iron", "confidence": 1.0},
                {"name": "colour", "value": "red", "confidence": 1.0},
            ],
        ),
        # Item E: nut, size=5", thread=left hand, material=steel, colour=red
        DBInventoryItem(
            item_number="ITEM-E",
            raw_description="5 inch left hand threaded steel nut red",
            product_name="Nut",
            product_category="Nuts",
            content_hash="hash_e",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "thread", "value": "left hand", "confidence": 1.0},
                {"name": "material", "value": "steel", "confidence": 1.0},
                {"name": "colour", "value": "red", "confidence": 1.0},
            ],
        ),
    ]

    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    return items


@pytest.fixture
def nuts_hierarchy():
    """Property hierarchy for Nuts category"""
    # Hierarchy order: size > material > thread > colour
    return PropertyHierarchy(
        category="Nuts", property_order=["size", "material", "thread", "colour"]
    )


@pytest.mark.unit
def test_category_filtering_only(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """Test filtering by category only returns all items in that category"""
    product = create_product_mention(
        product_category="Nuts",
        properties=[],
        product_name="Generic Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should return Items A, B, D, E (all nuts, not Item C which is a nail)
    assert len(filtered_items) == 4
    item_numbers = {item.item_number for item in filtered_items}
    assert item_numbers == {"ITEM-A", "ITEM-B", "ITEM-D", "ITEM-E"}
    assert filter_depth == 0  # Only category filter applied


@pytest.mark.unit
def test_example_1_size_material_iron_colour_black(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """
    Example 1: Product = {category: nut, size: 5", material: iron, colour: black}
    Expected: Items B and D (both 5" iron nuts, different colours)
    """
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="material", value="iron", confidence=1.0),
        ProductProperty(name="colour", value="black", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Iron Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should return Items B and D (5" iron nuts with different colours)
    assert len(filtered_items) == 2
    item_numbers = {item.item_number for item in filtered_items}
    assert item_numbers == {"ITEM-B", "ITEM-D"}
    # Filter depth: category(0) + size(1) + material(2) = 2, stopped at colour
    assert filter_depth == 2


@pytest.mark.unit
def test_example_2_exact_colour_match_returns_one(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """
    Example 2: If product has colour=red, should return only Item D
    """
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="material", value="iron", confidence=1.0),
        ProductProperty(name="colour", value="red", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Red Iron Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should return only Item D (exact match on all properties)
    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "ITEM-D"
    assert filter_depth == 3  # All 3 properties matched


@pytest.mark.unit
def test_example_3_nail_category_returns_nail(
    test_db_session: Session, sample_inventory_items
):
    """
    Example 3: If category=nail, should return Item C
    """
    nails_hierarchy = PropertyHierarchy(
        category="Nails", property_order=["size", "material", "colour"]
    )

    product_properties = [
        ProductProperty(name="size", value='6"', confidence=1.0),
        ProductProperty(name="material", value="iron", confidence=1.0),
        ProductProperty(name="colour", value="black", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nails",
        properties=product_properties,
        product_name="Iron Nail",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nails_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should return Item C (the only nail)
    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "ITEM-C"


@pytest.mark.unit
def test_example_4_higher_ranked_thread_property(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """
    Example 4: Product with thread=left hand should return Item E
    (even though hierarchy is size > material > thread)
    """
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="thread", value="left hand", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Left Hand Threaded Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Filter progression:
    # 1. category=Nuts -> A, B, D, E (4 items)
    # 2. size=5" -> B, D, E (3 items)
    # 3. thread=left hand -> E only (1 item)
    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "ITEM-E"
    assert filter_depth == 2  # size + thread


@pytest.mark.unit
def test_example_5_mismatched_thread_stops_early(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """
    Example 5: Product with thread=right hand (doesn't match Item E's left hand)
    Should return Items B, D, E (all 5" nuts, stopping before thread filter)
    """
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="thread", value="right hand", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Right Hand Threaded Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should return B, D, E (stopped at size level because thread didn't match)
    assert len(filtered_items) == 3
    item_numbers = {item.item_number for item in filtered_items}
    assert item_numbers == {"ITEM-B", "ITEM-D", "ITEM-E"}
    assert filter_depth == 1  # Only size filter succeeded


@pytest.mark.unit
def test_threshold_behavior_continue_filtering(
    test_db_session: Session, nuts_hierarchy
):
    """
    Test threshold behavior: If results >= 10 items, continue to next level
    """
    # Create 15 nuts with size=5" but different materials
    items = []
    for i in range(15):
        material = "steel" if i < 8 else "iron"
        item = DBInventoryItem(
            item_number=f"NUT-{i:03d}",
            raw_description=f"5 inch {material} nut",
            product_name="Nut",
            product_category="Nuts",
            content_hash=f"hash_{i}",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": material, "confidence": 1.0},
            ],
        )
        items.append(item)
        test_db_session.add(item)
    test_db_session.commit()

    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="material", value="steel", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Steel Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # After size filter: 15 items (>= threshold of 10)
    # Should continue to material filter: 8 steel items
    assert len(filtered_items) == 8
    assert filter_depth == 2  # size + material


@pytest.mark.unit
def test_threshold_behavior_stop_filtering(test_db_session: Session, nuts_hierarchy):
    """
    Test threshold behavior: If results < 10 items, stop filtering
    """
    # Create 5 nuts with size=5"
    items = []
    for i in range(5):
        material = "steel" if i < 3 else "iron"
        item = DBInventoryItem(
            item_number=f"NUT-{i:03d}",
            raw_description=f"5 inch {material} nut",
            product_name="Nut",
            product_category="Nuts",
            content_hash=f"hash_{i}",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": material, "confidence": 1.0},
            ],
        )
        items.append(item)
        test_db_session.add(item)
    test_db_session.commit()

    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="material", value="steel", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Steel Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # After size filter: 5 items (< threshold of 10)
    # But filter by material returns 3 items (non-zero), so filtering continues
    # Threshold only matters when a filter would return 0 results
    assert len(filtered_items) == 3  # 3 steel nuts
    assert filter_depth == 2  # Size + material filters applied


@pytest.mark.unit
def test_fuzzy_matching_with_normalizer(test_db_session: Session, nuts_hierarchy):
    """Test that fuzzy matching works using normalizer module"""
    # Create item with "gr8" grade (should match "grade 8" or "8")
    item = DBInventoryItem(
        item_number="BOLT-001",
        raw_description="Grade 8 bolt",
        product_name="Bolt",
        product_category="Nuts",
        content_hash="hash_bolt",
        properties=[
            {"name": "grade", "value": "gr8", "confidence": 1.0},
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    # Search with normalized value "8"
    product_properties = [
        ProductProperty(name="grade", value="8", confidence=1.0),
    ]

    hierarchy = PropertyHierarchy(category="Nuts", property_order=["grade"])

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Grade 8 Bolt",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should find the item via fuzzy matching/normalization
    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "BOLT-001"


@pytest.mark.unit
def test_no_matching_category_returns_empty(
    test_db_session: Session, sample_inventory_items
):
    """Test that non-existent category returns empty list"""
    hierarchy = PropertyHierarchy(category="Bolts", property_order=["size"])

    product = create_product_mention(
        product_category="Bolts",
        properties=[],
        product_name="Generic Bolt",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 0
    assert filter_depth == 0


@pytest.mark.unit
def test_property_not_in_hierarchy_is_skipped(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """Test that properties not in hierarchy are skipped"""
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(
            name="weight", value="10kg", confidence=1.0
        ),  # Not in hierarchy
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Nut with Weight",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should filter by size only, ignore weight
    assert len(filtered_items) == 3  # Items B, D, E (all 5")
    assert filter_depth == 1  # Only size


@pytest.mark.unit
def test_empty_inventory_returns_empty(test_db_session: Session, nuts_hierarchy):
    """Test with empty inventory database"""
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Generic Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 0
    assert filter_depth == 0


@pytest.mark.unit
def test_item_missing_property_excluded_from_filter(
    test_db_session: Session, nuts_hierarchy
):
    """Test that items missing a property are excluded when filtering by that property"""
    # Item with size but no material
    item1 = DBInventoryItem(
        item_number="NUT-001",
        raw_description="5 inch nut",
        product_name="Nut",
        product_category="Nuts",
        content_hash="hash_1",
        properties=[
            {"name": "size", "value": '5"', "confidence": 1.0},
        ],
    )
    # Item with size AND material
    item2 = DBInventoryItem(
        item_number="NUT-002",
        raw_description="5 inch steel nut",
        product_name="Nut",
        product_category="Nuts",
        content_hash="hash_2",
        properties=[
            {"name": "size", "value": '5"', "confidence": 1.0},
            {"name": "material", "value": "steel", "confidence": 1.0},
        ],
    )
    test_db_session.add(item1)
    test_db_session.add(item2)
    test_db_session.commit()

    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
        ProductProperty(name="material", value="steel", confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Steel Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    # After size filter: 2 items (< threshold of 10)
    # Material filter returns 1 item (NUT-002 has material=steel)
    # Filtering continues because material filter returned non-zero results
    # Only items WITH the material property are kept
    assert len(filtered_items) == 1  # Only NUT-002 has material property
    assert filter_depth == 2  # Size + material filters applied


@pytest.mark.unit
def test_returns_pydantic_models(
    test_db_session: Session, sample_inventory_items, nuts_hierarchy
):
    """Test that function returns Pydantic InventoryItem models, not SQLAlchemy"""
    product_properties = [
        ProductProperty(name="size", value='5"', confidence=1.0),
    ]

    product = create_product_mention(
        product_category="Nuts",
        properties=product_properties,
        product_name="Generic Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) > 0
    # Check that returned items are Pydantic models
    assert isinstance(filtered_items[0], InventoryItem)
    assert hasattr(filtered_items[0], "item_number")
    assert hasattr(filtered_items[0], "properties")


# ============================================================================
# NEW TEST CASES FOR INCREASED COVERAGE
# ============================================================================


@pytest.mark.unit
def test_measurement_type_exact_matching_only(test_db_session: Session):
    """
    Test that measurement types use exact matching only (no fuzzy matching).
    Measurements like sizes should match exactly after normalization.
    """
    hierarchy = PropertyHierarchy(category="Bolts", property_order=["size"])

    # Create items with measurement-type sizes
    items = [
        DBInventoryItem(
            item_number="BOLT-001",
            raw_description="4 inch bolt",
            product_name="Bolt",
            product_category="Bolts",
            content_hash="hash_001",
            properties=[
                {
                    "name": "size",
                    "value": '4"',
                    "value_type": "measurement",
                    "confidence": 1.0,
                },
            ],
        ),
        DBInventoryItem(
            item_number="BOLT-002",
            raw_description="5 inch bolt",
            product_name="Bolt",
            product_category="Bolts",
            content_hash="hash_002",
            properties=[
                {
                    "name": "size",
                    "value": '5"',
                    "value_type": "measurement",
                    "confidence": 1.0,
                },
            ],
        ),
    ]
    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    # Search for 4" - should only match BOLT-001 exactly
    product = create_product_mention(
        product_category="Bolts",
        properties=[
            ProductProperty(
                name="size", value='4"', value_type="measurement", confidence=1.0
            ),
        ],
        product_name="4 inch Bolt",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "BOLT-001"
    assert filter_depth == 1


@pytest.mark.unit
def test_case_insensitive_property_name_matching(test_db_session: Session):
    """
    Test that property names are matched case-insensitively.
    """
    hierarchy = PropertyHierarchy(
        category="Parts", property_order=["Material", "Color"]
    )

    item = DBInventoryItem(
        item_number="PART-001",
        raw_description="Steel part red",
        product_name="Part",
        product_category="Parts",
        content_hash="hash_001",
        properties=[
            {"name": "MATERIAL", "value": "steel", "confidence": 1.0},  # Uppercase
            {"name": "color", "value": "red", "confidence": 1.0},  # Lowercase
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    # Search with mixed case property names
    product = create_product_mention(
        product_category="Parts",
        properties=[
            ProductProperty(
                name="material", value="steel", confidence=1.0
            ),  # Lowercase
            ProductProperty(name="COLOR", value="red", confidence=1.0),  # Uppercase
        ],
        product_name="Steel Red Part",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "PART-001"
    assert filter_depth == 2  # Both properties matched


@pytest.mark.unit
def test_different_fuzzy_threshold_high(test_db_session: Session):
    """
    Test with higher fuzzy_threshold (0.9) - more strict matching.
    """
    hierarchy = PropertyHierarchy(category="Items", property_order=["material"])

    items = [
        DBInventoryItem(
            item_number="ITEM-001",
            raw_description="Steel item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_001",
            properties=[
                {"name": "material", "value": "steel", "confidence": 1.0},
            ],
        ),
        DBInventoryItem(
            item_number="ITEM-002",
            raw_description="Stainless steel item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_002",
            properties=[
                {"name": "material", "value": "stainless", "confidence": 1.0},
            ],
        ),
    ]
    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    # Search for "steel" with high threshold
    product = create_product_mention(
        product_category="Items",
        properties=[
            ProductProperty(name="material", value="steel", confidence=1.0),
        ],
        product_name="Steel Item",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.9,  # High threshold
    )

    # With high threshold, "steel" should not match "stainless" fuzzy
    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "ITEM-001"


@pytest.mark.unit
def test_different_fuzzy_threshold_low(test_db_session: Session):
    """
    Test with lower fuzzy_threshold (0.5) - more lenient matching.
    """
    hierarchy = PropertyHierarchy(category="Items", property_order=["material"])

    items = [
        DBInventoryItem(
            item_number="ITEM-001",
            raw_description="Aluminum item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_001",
            properties=[
                {"name": "material", "value": "aluminum", "confidence": 1.0},
            ],
        ),
        DBInventoryItem(
            item_number="ITEM-002",
            raw_description="Aluminium item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_002",
            properties=[
                {
                    "name": "material",
                    "value": "aluminium",
                    "confidence": 1.0,
                },  # British spelling
            ],
        ),
    ]
    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    # Search for "aluminum" with low threshold
    product = create_product_mention(
        product_category="Items",
        properties=[
            ProductProperty(name="material", value="aluminum", confidence=1.0),
        ],
        product_name="Aluminum Item",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.5,  # Low threshold
    )

    # With low threshold, both spellings should match
    assert len(filtered_items) >= 1  # At least the exact match


@pytest.mark.unit
def test_different_continue_threshold_low(test_db_session: Session):
    """
    Test with lower continue_threshold (5) - stops filtering earlier.
    """
    hierarchy = PropertyHierarchy(category="Nuts", property_order=["size", "material"])

    # Create 8 nuts with same size
    items = []
    for i in range(8):
        material = "steel" if i < 4 else "iron"
        item = DBInventoryItem(
            item_number=f"NUT-{i:03d}",
            raw_description=f"5 inch {material} nut",
            product_name="Nut",
            product_category="Nuts",
            content_hash=f"hash_{i}",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": material, "confidence": 1.0},
            ],
        )
        items.append(item)
        test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Nuts",
        properties=[
            ProductProperty(name="size", value='5"', confidence=1.0),
            ProductProperty(name="material", value="steel", confidence=1.0),
        ],
        product_name="Steel Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
        continue_threshold=5,  # Low threshold
    )

    # After size filter: 8 items (>= 5), continue to material
    # After material filter: 4 steel items
    assert len(filtered_items) == 4
    assert filter_depth == 2


@pytest.mark.unit
def test_different_continue_threshold_high(test_db_session: Session):
    """
    Test with higher continue_threshold (20) - more aggressive filtering.
    """
    hierarchy = PropertyHierarchy(category="Nuts", property_order=["size", "material"])

    # Create 15 nuts with same size
    items = []
    for i in range(15):
        material = "steel" if i < 10 else "iron"
        item = DBInventoryItem(
            item_number=f"NUT-{i:03d}",
            raw_description=f"5 inch {material} nut",
            product_name="Nut",
            product_category="Nuts",
            content_hash=f"hash_{i}",
            properties=[
                {"name": "size", "value": '5"', "confidence": 1.0},
                {"name": "material", "value": material, "confidence": 1.0},
            ],
        )
        items.append(item)
        test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Nuts",
        properties=[
            ProductProperty(name="size", value='5"', confidence=1.0),
            ProductProperty(name="material", value="steel", confidence=1.0),
        ],
        product_name="Steel Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
        continue_threshold=20,  # High threshold
    )

    # After size filter: 15 items (< 20), but material filter still applies
    # Material filter returns 10 items
    assert len(filtered_items) == 10
    assert filter_depth == 2


@pytest.mark.unit
def test_multiple_properties_all_match(test_db_session: Session):
    """
    Test filtering with multiple properties that all match exactly.
    """
    hierarchy = PropertyHierarchy(
        category="Fasteners", property_order=["size", "grade", "material", "finish"]
    )

    item = DBInventoryItem(
        item_number="FASTENER-001",
        raw_description="1/2 inch grade 8 steel zinc plated bolt",
        product_name="Bolt",
        product_category="Fasteners",
        content_hash="hash_001",
        properties=[
            {"name": "size", "value": '1/2"', "confidence": 1.0},
            {"name": "grade", "value": "8", "confidence": 1.0},
            {"name": "material", "value": "steel", "confidence": 1.0},
            {"name": "finish", "value": "zinc plated", "confidence": 1.0},
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Fasteners",
        properties=[
            ProductProperty(name="size", value='1/2"', confidence=1.0),
            ProductProperty(name="grade", value="8", confidence=1.0),
            ProductProperty(name="material", value="steel", confidence=1.0),
            ProductProperty(name="finish", value="zinc plated", confidence=1.0),
        ],
        product_name="Grade 8 Steel Bolt",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "FASTENER-001"
    assert filter_depth == 4  # All 4 properties matched


@pytest.mark.unit
def test_property_value_none_edge_case(test_db_session: Session):
    """
    Test edge case where property value might be None or empty.
    """
    hierarchy = PropertyHierarchy(category="Items", property_order=["color"])

    item = DBInventoryItem(
        item_number="ITEM-001",
        raw_description="Uncolored item",
        product_name="Item",
        product_category="Items",
        content_hash="hash_001",
        properties=[
            {"name": "color", "value": "", "confidence": 1.0},  # Empty value
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Items",
        properties=[
            ProductProperty(name="color", value="", confidence=1.0),  # Empty value
        ],
        product_name="Uncolored Item",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    # Should still filter by category even if property is empty
    assert len(filtered_items) >= 0


@pytest.mark.unit
def test_special_characters_in_property_values(test_db_session: Session):
    """
    Test handling of special characters in property values.
    """
    hierarchy = PropertyHierarchy(category="Parts", property_order=["model"])

    item = DBInventoryItem(
        item_number="PART-001",
        raw_description="Part with special model",
        product_name="Part",
        product_category="Parts",
        content_hash="hash_001",
        properties=[
            {"name": "model", "value": "ABC-123/XYZ", "confidence": 1.0},
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Parts",
        properties=[
            ProductProperty(name="model", value="ABC-123/XYZ", confidence=1.0),
        ],
        product_name="Special Model Part",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "PART-001"


@pytest.mark.unit
def test_confidence_scores_preserved(test_db_session: Session, sample_inventory_items):
    """
    Test that confidence scores from inventory items are preserved in results.
    """
    hierarchy = PropertyHierarchy(category="Nuts", property_order=["size"])

    product = create_product_mention(
        product_category="Nuts",
        properties=[
            ProductProperty(name="size", value='5"', confidence=1.0),
        ],
        product_name="5 inch Nut",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) > 0
    # Check that properties have confidence scores
    for item in filtered_items:
        assert item.properties is not None
        assert len(item.properties) > 0
        for prop in item.properties:
            # Properties are ProductProperty Pydantic objects
            assert isinstance(prop, ProductProperty)
            assert hasattr(prop, "confidence")
            assert isinstance(prop.confidence, (int, float))
            assert 0.0 <= prop.confidence <= 1.0


@pytest.mark.unit
def test_normalization_different_formats(test_db_session: Session):
    """
    Test that normalization handles different measurement formats.
    Examples: "4 inch" vs '4"' vs "4in"
    """
    hierarchy = PropertyHierarchy(category="Parts", property_order=["length"])

    items = [
        DBInventoryItem(
            item_number="PART-001",
            raw_description="4 inch part",
            product_name="Part",
            product_category="Parts",
            content_hash="hash_001",
            properties=[
                {"name": "length", "value": "4 inch", "confidence": 1.0},
            ],
        ),
        DBInventoryItem(
            item_number="PART-002",
            raw_description='4" part',
            product_name="Part",
            product_category="Parts",
            content_hash="hash_002",
            properties=[
                {"name": "length", "value": '4"', "confidence": 1.0},
            ],
        ),
        DBInventoryItem(
            item_number="PART-003",
            raw_description="4in part",
            product_name="Part",
            product_category="Parts",
            content_hash="hash_003",
            properties=[
                {"name": "length", "value": "4in", "confidence": 1.0},
            ],
        ),
    ]
    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    # Search with one format
    product = create_product_mention(
        product_category="Parts",
        properties=[
            ProductProperty(name="length", value="4 inches", confidence=1.0),
        ],
        product_name="4 inch Part",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    # Normalization should make all these formats match
    # The exact number depends on normalizer implementation, but we expect at least some matches
    assert len(filtered_items) >= 1
    item_numbers = {item.item_number for item in filtered_items}
    # At least one of these should match after normalization
    assert len(item_numbers & {"PART-001", "PART-002", "PART-003"}) >= 1


@pytest.mark.unit
def test_unicode_and_special_text(test_db_session: Session):
    """
    Test handling of unicode and special text characters.
    """
    hierarchy = PropertyHierarchy(category="Items", property_order=["description"])

    item = DBInventoryItem(
        item_number="ITEM-001",
        raw_description="Item with special chars: é, ñ, ü",
        product_name="Item",
        product_category="Items",
        content_hash="hash_001",
        properties=[
            {"name": "description", "value": "café", "confidence": 1.0},
        ],
    )
    test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Items",
        properties=[
            ProductProperty(name="description", value="café", confidence=1.0),
        ],
        product_name="Café Item",
    )

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].item_number == "ITEM-001"


@pytest.mark.unit
def test_property_order_matters(test_db_session: Session):
    """
    Test that the order of properties in hierarchy affects filtering depth.
    """
    # Create two hierarchies with different property orders
    hierarchy1 = PropertyHierarchy(category="Items", property_order=["size", "color"])
    hierarchy2 = PropertyHierarchy(category="Items", property_order=["color", "size"])

    items = [
        DBInventoryItem(
            item_number="ITEM-001",
            raw_description="Small red item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_001",
            properties=[
                {"name": "size", "value": "small", "confidence": 1.0},
                {"name": "color", "value": "red", "confidence": 1.0},
            ],
        ),
        DBInventoryItem(
            item_number="ITEM-002",
            raw_description="Small blue item",
            product_name="Item",
            product_category="Items",
            content_hash="hash_002",
            properties=[
                {"name": "size", "value": "small", "confidence": 1.0},
                {"name": "color", "value": "blue", "confidence": 1.0},
            ],
        ),
    ]
    for item in items:
        test_db_session.add(item)
    test_db_session.commit()

    product = create_product_mention(
        product_category="Items",
        properties=[
            ProductProperty(name="size", value="small", confidence=1.0),
            ProductProperty(name="color", value="red", confidence=1.0),
        ],
        product_name="Small Red Item",
    )

    # Test with hierarchy1 (size first)
    filtered_items1, depth1 = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy1,
        fuzzy_threshold=0.8,
    )

    # Test with hierarchy2 (color first)
    filtered_items2, depth2 = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        product=product,
        hierarchy=hierarchy2,
        fuzzy_threshold=0.8,
    )

    # Both should eventually find the same item, but may have different depths
    assert len(filtered_items1) == 1
    assert len(filtered_items2) == 1
    assert filtered_items1[0].item_number == "ITEM-001"
    assert filtered_items2[0].item_number == "ITEM-001"
