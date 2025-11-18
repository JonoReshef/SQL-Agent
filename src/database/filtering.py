"""Database-driven hierarchical filtering for inventory matching"""

from typing import List, Tuple

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from src.database.models import InventoryItem as DBInventoryItem
from src.matching.hierarchy import PropertyHierarchy  # Direct import to avoid __init__
from src.matching.normalizer import normalize_property_value  # Direct import
from src.models.inventory import InventoryItem
from src.models.product import ProductProperty


def filter_inventory_by_hierarchical_properties(
    session: Session,
    category: str,
    properties: List[ProductProperty],
    hierarchy: PropertyHierarchy,
    fuzzy_threshold: float = 0.8,
    continue_threshold: int = 10,
) -> Tuple[List[InventoryItem], int]:
    """
    Progressively filter inventory using hierarchical properties with database queries.

    Filters by category first, then applies property filters in hierarchy order.
    Stops filtering when result set drops below continue_threshold.
    Uses fuzzy matching via normalizer for property value matching.

    Args:
        session: SQLAlchemy database session
        category: Product category to filter by
        properties: List of product properties to match
        hierarchy: Property hierarchy defining filter order
        fuzzy_threshold: Minimum similarity for fuzzy property matching (0.0-1.0)
        continue_threshold: Minimum items to continue filtering (default 10)

    Returns:
        Tuple of:
        - List of InventoryItem Pydantic models
        - filter_depth: Number of hierarchy levels successfully applied

    Example:
        >>> filtered, depth = filter_inventory_by_hierarchical_properties(
        ...     session=db_session,
        ...     category="Nuts",
        ...     properties=[
        ...         ProductProperty(name="size", value="5\"", confidence=1.0),
        ...         ProductProperty(name="material", value="iron", confidence=1.0),
        ...     ],
        ...     hierarchy=nuts_hierarchy,
        ... )
    """
    # Step 1: Filter by category
    query = session.query(DBInventoryItem).filter(
        DBInventoryItem.product_category == category
    )

    last_valid_results = query.all()
    filter_depth = 0

    if not last_valid_results:
        # No items in this category
        return [], 0

    # Create property lookup by name (case-insensitive)
    product_props_by_name = {prop.name.lower(): prop for prop in properties}

    # Step 2: Apply property filters in hierarchy order
    filters_applied = 0  # Track how many filters were actually applied

    for level_idx, property_name in enumerate(hierarchy.property_order):
        property_name_lower = property_name.lower()

        # Skip if product doesn't have this property
        if property_name_lower not in product_props_by_name:
            continue

        product_prop = product_props_by_name[property_name_lower]

        # Normalize the product property value for matching
        normalized_product_value = normalize_property_value(
            product_prop.name,
            product_prop.value,
            fuzzy_threshold=int(fuzzy_threshold * 100),
        )

        # Filter items in memory (fetch from last_valid_results)
        candidates = []

        for db_item in last_valid_results:
            # Check if this item has the property and if it matches
            item_has_matching_property = False

            for inv_prop in db_item.properties:
                if inv_prop.get("name", "").lower() == property_name_lower:
                    # Found the property, now check if value matches
                    inv_value = inv_prop.get("value", "")
                    normalized_inv_value = normalize_property_value(
                        property_name,
                        inv_value,
                        fuzzy_threshold=int(fuzzy_threshold * 100),
                    )

                    # Exact match on normalized values
                    if normalized_product_value.lower() == normalized_inv_value.lower():
                        item_has_matching_property = True
                        break

                    # Fuzzy string matching on normalized values
                    similarity = (
                        fuzz.ratio(
                            normalized_product_value.lower(),
                            normalized_inv_value.lower(),
                        )
                        / 100.0
                    )

                    if similarity >= fuzzy_threshold:
                        item_has_matching_property = True
                        break

            if item_has_matching_property:
                candidates.append(db_item)

        # Check if filtering produced results
        if not candidates:
            # No matches at this level - filter returned 0 results
            # Apply threshold logic: only stop if previous result set was small
            if len(last_valid_results) < continue_threshold:
                # Previous set was small (< 10), stop and return it
                break
            else:
                # Previous set was large (>= 10), continue to try narrow it down
                # Don't update results, keep previous and try next filter
                continue

        # We got valid candidates (> 0 results), update results and continue
        last_valid_results = candidates
        filters_applied += 1

    filter_depth = filters_applied

    # Convert SQLAlchemy models to Pydantic models
    pydantic_items = []
    for db_item in last_valid_results:
        # Convert JSON properties to ProductProperty objects
        props = [
            ProductProperty(
                name=p.get("name", ""),
                value=p.get("value", ""),
                confidence=p.get("confidence", 1.0),
            )
            for p in db_item.properties
        ]

        pydantic_item = InventoryItem(
            item_number=db_item.item_number,
            raw_description=db_item.raw_description,
            exact_product_text=db_item.raw_description,  # Use raw_description as exact_product_text
            product_name=db_item.product_name or "",
            product_category=db_item.product_category or "",
            properties=props,
            parse_confidence=db_item.parse_confidence or 1.0,  # Default to 1.0 if None
            needs_manual_review=db_item.needs_manual_review or False,
        )
        pydantic_items.append(pydantic_item)

    return pydantic_items, filter_depth
