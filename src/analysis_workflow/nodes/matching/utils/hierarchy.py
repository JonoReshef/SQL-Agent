"""Property hierarchy management for hierarchical matching"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml


class PropertyHierarchy:
    """Represents the property matching hierarchy for a product category"""

    def __init__(self, category: str, property_order: List[str]):
        """
        Initialize a property hierarchy.

        Args:
            category: Product category name
            property_order: Ordered list of property names (most to least important)
        """
        self.category = category
        self._property_order = tuple(property_order)  # Immutable
        self._rank_map = {prop: idx for idx, prop in enumerate(property_order)}

    @property
    def property_order(self) -> List[str]:
        """Get the ordered list of properties"""
        return list(self._property_order)

    def get_rank(self, property_name: str) -> Optional[int]:
        """
        Get the rank/priority of a property in the hierarchy.

        Args:
            property_name: Name of the property

        Returns:
            Integer rank (0 = highest priority), or None if not in hierarchy
        """
        return self._rank_map.get(property_name.lower())

    def __repr__(self) -> str:
        return f"PropertyHierarchy(category='{self.category}', properties={self.property_order})"


@lru_cache(maxsize=32)
def get_hierarchy_for_category(category: str) -> Optional[PropertyHierarchy]:
    """
    Load property hierarchy for a category from products_config.yaml.

    This function is cached to avoid repeatedly parsing the config file.

    Args:
        category: Product category name (case-insensitive)

    Returns:
        PropertyHierarchy object, or None if category not found
    """
    config_path = "config/products_config.yaml"

    if not Path(config_path).exists():
        return None

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        products = config.get("products", [])
        category_lower = category.lower()

        for product in products:
            if product.get("category", "").lower() == category_lower:
                # Extract property names in order from config
                properties = product.get("properties", [])
                # Sort properties by priority (lower number = higher priority)
                sorted_properties = sorted(
                    properties, key=lambda p: p.get("priority", float("inf"))
                )
                property_order = [
                    prop["name"] for prop in sorted_properties if "name" in prop
                ]

                if property_order:
                    return PropertyHierarchy(
                        category=product["category"], property_order=property_order
                    )

        return None

    except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
        # Log error but return None gracefully
        print(f"Warning: Could not load hierarchy for category '{category}': {e}")
        return None


def get_all_hierarchies() -> dict[str, PropertyHierarchy]:
    """
    Load all property hierarchies from config.

    Returns:
        Dictionary mapping category name to PropertyHierarchy
    """
    config_path = (
        Path(__file__).parent.parent.parent / "config" / "products_config.yaml"
    )

    hierarchies = {}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        products = config.get("products", [])

        for product in products:
            category = product.get("category")
            if not category:
                continue

            properties = product.get("properties", [])
            property_order = [prop["name"] for prop in properties if "name" in prop]

            if property_order:
                hierarchies[category] = PropertyHierarchy(
                    category=category, property_order=property_order
                )

    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Warning: Could not load hierarchies from config: {e}")

    return hierarchies
