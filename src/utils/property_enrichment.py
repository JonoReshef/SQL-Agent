"""Utility functions for enriching product properties with config metadata"""

from typing import List

from src.analysis_workflow.nodes.matching.utils.hierarchy import get_hierarchy_for_category
from src.config.config_loader import load_config
from src.models.configs import ProductConfig
from src.models.product import ProductProperty

CONFIG = load_config()


def enrich_properties_with_metadata(
    properties: List[ProductProperty],
    category: str,
    config: ProductConfig | None = None,
) -> List[ProductProperty]:
    """
    Enrich product properties with value_type and priority from config.

    This function looks up each property in the config file and adds
    the correct value_type and priority based on the product category.

    Args:
        properties: List of ProductProperty objects (potentially from AI extraction)
        category: Product category to look up properties for
        config: Optional ProductConfig (loaded if not provided)

    Returns:
        List of enriched ProductProperty objects with correct value_type, priority and the properties are sorted based on hierarchy order.

    Example:
        >>> props = [
        ...     ProductProperty(name="grade", value="8", confidence=0.95),
        ...     ProductProperty(name="size", value="1/2-13", confidence=0.90),
        ... ]
        >>> enriched = enrich_properties_with_metadata(props, "Fasteners")
        >>> enriched[0].value_type  # "measurement" from config
        >>> enriched[0].priority    # 1 from config
    """
    if config is None:
        config = CONFIG

    enriched_properties = []

    hierarchy = get_hierarchy_for_category(category)  # Validate category exists

    if hierarchy is not None:
        # Sort properties based on hierarchy order
        property_order = {prop_name: idx for idx, prop_name in enumerate(hierarchy.property_order)}
        properties.sort(key=lambda p: property_order.get(p.name, len(property_order)))

    for prop in properties:
        # Get metadata from config
        value_type, priority = config.get_property_metadata(category, prop.name)

        # Create new property with enriched metadata
        enriched_prop = ProductProperty(
            name=prop.name,
            value=prop.value,
            confidence=prop.confidence,
            value_type=value_type,  # type: ignore  # From config, validated above
            priority=priority,  # From config
        )

        enriched_properties.append(enriched_prop)

    return enriched_properties
