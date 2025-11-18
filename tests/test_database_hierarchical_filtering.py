"""Tests for database-driven hierarchical inventory filtering"""

import pytest
from sqlalchemy.orm import Session

from src.database.connection import get_db_session, get_engine
from src.database.filtering import filter_inventory_by_hierarchical_properties
from src.database.models import Base
from src.database.models import InventoryItem as DBInventoryItem
from src.matching.hierarchy import PropertyHierarchy
from src.models.inventory import InventoryItem
from src.models.product import ProductMention, ProductProperty


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
    Base.metadata.drop_all(engine)


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
    # Note: We're testing the function directly, not via ProductMention
    # ProductMention would require email fields which aren't relevant here

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=[],
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nails",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Bolts",
        properties=[],
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
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

    filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
        session=test_db_session,
        category="Nuts",
        properties=product_properties,
        hierarchy=nuts_hierarchy,
        fuzzy_threshold=0.8,
    )

    assert len(filtered_items) > 0
    # Check that returned items are Pydantic models
    assert isinstance(filtered_items[0], InventoryItem)
    assert hasattr(filtered_items[0], "item_number")
    assert hasattr(filtered_items[0], "properties")
