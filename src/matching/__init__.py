"""Hierarchical product-to-inventory matching system"""

from .hierarchy import PropertyHierarchy, get_hierarchy_for_category
from .normalizer import (
    batch_normalize_properties,
    calculate_property_similarity,
    find_matching_properties,
    normalize_property_value,
)

# Lazy import for matcher to avoid circular dependency
# Use: from src.matching.matcher import match_product_to_inventory
# Instead of: from src.matching import match_product_to_inventory

__all__ = [
    "PropertyHierarchy",
    "get_hierarchy_for_category",
    "normalize_property_value",
    "batch_normalize_properties",
    "calculate_property_similarity",
    "find_matching_properties",
]
