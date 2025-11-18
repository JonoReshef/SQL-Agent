"""Hierarchical product-to-inventory matcher with database-driven filtering"""

from typing import List, Tuple

from rapidfuzz import fuzz

from src.database.connection import get_db_session, get_engine
from src.database.filtering import filter_inventory_by_hierarchical_properties
from src.matching.hierarchy import get_hierarchy_for_category
from src.matching.normalizer import find_matching_properties
from src.models.inventory import InventoryItem, InventoryMatch, ReviewFlag
from src.models.product import ProductMention


def match_product_to_inventory(
    product: ProductMention,
    inventory_items: List[InventoryItem],
    max_matches: int = 3,
    min_score: float = 0.5,
    review_threshold: float = 0.7,
) -> Tuple[List[InventoryMatch], List[ReviewFlag]]:
    """
    Match a product to inventory using hierarchical filtering and generate review flags if needed.

    Uses property hierarchy to progressively filter inventory via database queries,
    then scores and ranks the results. Generates review flags for quality issues.

    NOTE: inventory_items parameter is kept for backward compatibility but not used.
    Filtering is now done directly against the database for better performance.

    Args:
        product: Product mention from email
        inventory_items: List of inventory items (DEPRECATED - not used)
        max_matches: Maximum matches to return
        min_score: Minimum match score
        review_threshold: Threshold below which to flag for review

    Returns:
        Tuple of (matches, review_flags)
    """
    matches = find_best_matches(product, max_matches, min_score)

    review_flags = []

    # Generate review flags
    if not matches:
        review_flags.append(
            ReviewFlag(
                product_text=product.exact_product_text,
                product_name=product.product_name,
                product_category=product.product_category,
                issue_type="INSUFFICIENT_DATA",
                match_count=0,
                top_confidence=None,
                reason="No inventory matches found above minimum threshold",
                action_needed="Manual inventory search or create new inventory item",
            )
        )
    elif matches[0].match_score < review_threshold:
        review_flags.append(
            ReviewFlag(
                product_text=product.exact_product_text,
                product_name=product.product_name,
                product_category=product.product_category,
                issue_type="LOW_CONFIDENCE",
                match_count=len(matches),
                top_confidence=matches[0].match_score,
                reason=f"Top match has low confidence score ({matches[0].match_score:.2f})",
                action_needed=f"Review match with inventory item {matches[0].inventory_item_number}",
            )
        )
    elif (
        len(matches) > 1 and abs(matches[0].match_score - matches[1].match_score) < 0.1
    ):
        review_flags.append(
            ReviewFlag(
                product_text=product.exact_product_text,
                product_name=product.product_name,
                product_category=product.product_category,
                issue_type="AMBIGUOUS_MATCH",
                match_count=len(matches),
                top_confidence=matches[0].match_score,
                reason=f"Multiple similar matches with close scores ({matches[0].match_score:.2f} vs {matches[1].match_score:.2f})",
                action_needed=f"Verify best match between {matches[0].inventory_item_number} and {matches[1].inventory_item_number}",
            )
        )

    # Flag if properties are missing
    if (
        matches
        and matches[0].missing_properties
        and len(matches[0].missing_properties) >= 2
    ):
        review_flags.append(
            ReviewFlag(
                product_text=product.exact_product_text,
                product_name=product.product_name,
                product_category=product.product_category,
                issue_type="INSUFFICIENT_DATA",
                match_count=len(matches),
                top_confidence=matches[0].match_score,
                reason=f"Multiple properties missing in inventory match: {', '.join(matches[0].missing_properties)}",
                action_needed="Consider updating inventory item with additional property specifications",
            )
        )

    return matches, review_flags


def find_best_matches(
    product: ProductMention,
    max_matches: int = 3,
    min_score: float = 0.5,
) -> List[InventoryMatch]:
    """
    Find best matching inventory items for a product using database-driven hierarchical filtering.

    Uses property hierarchy to filter candidates via database queries, then scores and ranks results.

    Args:
        product: Product mention from email
        max_matches: Maximum number of matches to return
        min_score: Minimum match score threshold

    Returns:
        List of InventoryMatch objects, ranked by score
    """
    # Get property hierarchy for this category
    hierarchy = get_hierarchy_for_category(product.product_category)

    if hierarchy is None:
        # No hierarchy found, return empty list
        # Could fallback to querying all items in category, but that defeats the purpose
        return []

    # Use database-driven hierarchical filtering
    engine = get_engine()
    with get_db_session(engine) as session:
        filtered_items, filter_depth = filter_inventory_by_hierarchical_properties(
            session=session,
            category=product.product_category,
            properties=product.properties,
            hierarchy=hierarchy,
            fuzzy_threshold=0.8,
            continue_threshold=10,
        )

    if not filtered_items:
        return []

    # Score the filtered items
    matches = []

    for inv_item in filtered_items:
        score, matched_props, missing_props, reasoning = calculate_match_score(
            product, inv_item
        )

        if score >= min_score:
            match = InventoryMatch(
                inventory_item_number=inv_item.item_number,
                inventory_description=inv_item.raw_description,
                match_score=score,
                rank=1,  # Temporary, will be updated after sorting
                inventory_properties=inv_item.properties,
                matched_properties=matched_props,
                missing_properties=missing_props,
                match_reasoning=reasoning,
            )
            matches.append(match)

    # Sort by score (descending) and assign ranks
    matches.sort(key=lambda m: m.match_score, reverse=True)

    for idx, match in enumerate(matches[:max_matches]):
        match.rank = idx + 1

    return matches[:max_matches]


def calculate_match_score(
    product: ProductMention,
    inventory_item: InventoryItem,
    name_weight: float = 0.4,
    category_weight: float = 0.2,
    properties_weight: float = 0.4,
) -> Tuple[float, List[str], List[str], str]:
    """
    Calculate match score between a product mention and inventory item.

    Uses weighted combination of:
    - Product name similarity (fuzzy match)
    - Category match (exact or fuzzy)
    - Property overlap (based on hierarchy matching)

    Args:
        product: Product mention from email
        inventory_item: Inventory item to match against
        name_weight: Weight for name similarity (default 0.4)
        category_weight: Weight for category match (default 0.2)
        properties_weight: Weight for property overlap (default 0.4)

    Returns:
        Tuple of:
        - Overall match score (0.0 to 1.0)
        - List of matched property names
        - List of missing property names
        - Human-readable reasoning
    """
    # Name similarity
    name_similarity = (
        fuzz.ratio(product.product_name.lower(), inventory_item.product_name.lower())
        / 100.0
    )

    # Category match
    category_match = (
        1.0
        if product.product_category.lower() == inventory_item.product_category.lower()
        else fuzz.ratio(
            product.product_category.lower(), inventory_item.product_category.lower()
        )
        / 100.0
    )

    # Property overlap
    matched_props, missing_props, prop_scores = find_matching_properties(
        product.properties, inventory_item.properties, min_similarity=0.8
    )

    if len(product.properties) > 0:
        # Calculate match ratio: matched / total product properties
        property_match_ratio = len(matched_props) / len(product.properties)
    else:
        property_match_ratio = 0.5  # Neutral score if no properties

    # Weighted overall score
    overall_score = (
        name_weight * name_similarity
        + category_weight * category_match
        + properties_weight * property_match_ratio
    )

    # Generate reasoning
    reasoning_parts = []
    reasoning_parts.append(f"Name similarity: {name_similarity:.2f}")
    reasoning_parts.append(f"Category match: {category_match:.2f}")
    if matched_props:
        reasoning_parts.append(f"Matched properties: {', '.join(matched_props)}")
    if missing_props:
        reasoning_parts.append(f"Missing properties: {', '.join(missing_props)}")

    reasoning = ". ".join(reasoning_parts) + "."

    return overall_score, matched_props, missing_props, reasoning
