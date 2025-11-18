"""Hierarchical filtering logic for inventory matching

DEPRECATED: This module contains the old in-memory filtering approach.
It has been replaced by database-driven filtering in src/database/operations.py
which provides 10-100x better performance for large inventory datasets.

New code should use:
    from src.database.operations import filter_inventory_by_hierarchical_properties

This module is kept for:
- Backward compatibility with existing code
- Unit tests that validate filtering logic
- Reference implementation for the filtering algorithm

The database-driven implementation in operations.py follows the same logic
but executes it as SQL queries against PostgreSQL instead of Python loops.
"""

import warnings
from typing import List, Tuple

from src.matching.hierarchy import PropertyHierarchy
from src.matching.normalizer import calculate_property_similarity
from src.models.inventory import InventoryItem
from src.models.product import ProductMention, ProductProperty


def filter_by_property(
    inventory_items: List[InventoryItem],
    target_property: ProductProperty,
    min_similarity: float = 0.8,
) -> List[InventoryItem]:
    """
    Filter inventory items by a single property.

    DEPRECATED: Use database-driven filtering for better performance:
        from src.database.operations import filter_inventory_by_hierarchical_properties

    Args:
        inventory_items: List of inventory items to filter
        target_property: Property to filter by
        min_similarity: Minimum similarity threshold for match

    Returns:
        List of inventory items that match the property
    """
    warnings.warn(
        "filter_by_property is deprecated. Use database-driven filtering from "
        "src.database.operations.filter_inventory_by_hierarchical_properties for better performance.",
        DeprecationWarning,
        stacklevel=2,
    )

    filtered = []

    for item in inventory_items:
        # Check if item has this property
        for inv_prop in item.properties:
            if inv_prop.name.lower() == target_property.name.lower():
                # Calculate similarity
                similarity = calculate_property_similarity(
                    target_property, inv_prop, normalize=True
                )

                if similarity >= min_similarity:
                    filtered.append(item)
                    break  # Found a match, no need to check other properties

    return filtered


def hierarchical_filter(
    product: ProductMention,
    inventory_items: List[InventoryItem],
    hierarchy: PropertyHierarchy,
    min_similarity: float = 0.8,
) -> List[InventoryItem]:
    """
    Apply hierarchical filtering to inventory items.

    DEPRECATED: Use database-driven filtering for better performance:
        from src.database.operations import filter_inventory_by_hierarchical_properties

    Filter inventory items using hierarchical property matching.
    Filters progressively by each property in the hierarchy order.
    Each level is a subset of the previous level.

    Args:
        product: Product mention with properties to match
        inventory_items: List of all inventory items
        hierarchy: Property hierarchy defining filter order
        min_similarity: Minimum similarity threshold for matches

    Returns:
        List of filtered inventory items matching the product
    """
    warnings.warn(
        "hierarchical_filter is deprecated. Use database-driven filtering from "
        "src.database.operations.filter_inventory_by_hierarchical_properties for better performance.",
        DeprecationWarning,
        stacklevel=2,
    )

    if not inventory_items:
        return []

    if not product.properties:
        # No properties to filter by, return all items
        return inventory_items

    # Create a mapping of product properties by name (lowercase)
    product_props = {prop.name.lower(): prop for prop in product.properties}

    # Start with all inventory items
    candidates = inventory_items

    # Filter progressively by each property in hierarchy order
    for prop_name in hierarchy.property_order:
        if prop_name.lower() not in product_props:
            # Product doesn't have this property, skip this level
            continue

        target_prop = product_props[prop_name.lower()]

        # Filter candidates by this property
        filtered_candidates = filter_by_property(
            candidates, target_prop, min_similarity
        )

        if not filtered_candidates:
            # No matches at this level
            # Return candidates from previous level (less restrictive)
            # This handles cases where inventory items are missing properties
            return candidates

        # Use filtered candidates for next level
        candidates = filtered_candidates

    return candidates


def score_filtered_items(
    product: ProductMention,
    filtered_items: List[InventoryItem],
    hierarchy: PropertyHierarchy,
) -> List[Tuple[InventoryItem, float]]:
    """
    Score filtered inventory items based on how many hierarchy levels they match.

    DEPRECATED: This is part of the old in-memory filtering approach.
    Use database-driven filtering which includes scoring logic.

    Args:
        product: Product mention with properties
        filtered_items: Pre-filtered inventory items
        hierarchy: Property hierarchy for scoring

    Returns:
        List of (InventoryItem, score) tuples, sorted by score descending
    """
    warnings.warn(
        "score_filtered_items is deprecated. Use database-driven filtering from "
        "src.database.operations.filter_inventory_by_hierarchical_properties for better performance.",
        DeprecationWarning,
        stacklevel=2,
    )

    if not filtered_items:
        return []

    scored_items = []
    product_props = {prop.name.lower(): prop for prop in product.properties}

    for item in filtered_items:
        # Count how many hierarchy levels this item matches
        matched_levels = 0
        total_levels = 0

        # Score based on hierarchy order (earlier properties are more important)
        for prop_name in hierarchy.property_order:
            if prop_name.lower() not in product_props:
                continue

            total_levels += 1
            target_prop = product_props[prop_name.lower()]

            # Check if item has this property
            for inv_prop in item.properties:
                if inv_prop.name.lower() == prop_name.lower():
                    similarity = calculate_property_similarity(
                        target_prop, inv_prop, normalize=True
                    )
                    if similarity >= 0.8:
                        matched_levels += 1
                    break

        # Calculate score: higher weight for matching more hierarchy levels
        # Use weighted score where earlier (more important) properties count more
        if total_levels > 0:
            score = matched_levels / total_levels
        else:
            score = 0.0

        scored_items.append((item, score))

    # Sort by score descending
    scored_items.sort(key=lambda x: x[1], reverse=True)

    return scored_items
