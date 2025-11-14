"""Product-to-inventory matching engine"""

from typing import List, Tuple

from rapidfuzz import fuzz

from src.models.inventory import InventoryItem, InventoryMatch, ReviewFlag
from src.models.product import ProductMention

from .normalizer import find_matching_properties


def match_product_to_inventory(
    product: ProductMention,
    inventory_items: List[InventoryItem],
    max_matches: int = 3,
    min_score: float = 0.5,
    review_threshold: float = 0.7,
) -> Tuple[List[InventoryMatch], List[ReviewFlag]]:
    """
    Match a product to inventory and generate review flags if needed.

    Args:
        product: Product mention from email
        inventory_items: List of inventory items
        max_matches: Maximum matches to return
        min_score: Minimum match score
        review_threshold: Threshold below which to flag for review

    Returns:
        Tuple of (matches, review_flags)
    """
    matches = find_best_matches(product, inventory_items, max_matches, min_score)

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
    - Property overlap (Jaccard similarity)

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

    # Property overlap using Jaccard similarity
    matched_props, missing_props, prop_scores = find_matching_properties(
        product.properties, inventory_item.properties, min_similarity=0.8
    )

    if len(product.properties) > 0:
        # Jaccard similarity: |intersection| / |union|
        intersection = len(matched_props)
        union = len(
            set([p.name for p in product.properties])
            | set([p.name for p in inventory_item.properties])
        )
        property_overlap = intersection / union if union > 0 else 0.0
    else:
        property_overlap = 0.5  # Neutral score if no properties

    # Weighted overall score
    overall_score = (
        name_weight * name_similarity
        + category_weight * category_match
        + properties_weight * property_overlap
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


def find_best_matches(
    product: ProductMention,
    inventory_items: List[InventoryItem],
    max_matches: int = 3,
    min_score: float = 0.5,
) -> List[InventoryMatch]:
    """
    Find best matching inventory items for a product.

    Args:
        product: Product mention from email
        inventory_items: List of inventory items to match against
        max_matches: Maximum number of matches to return
        min_score: Minimum match score threshold

    Returns:
        List of InventoryMatch objects, ranked by score
    """
    matches = []

    for inv_item in inventory_items:
        score, matched_props, missing_props, reasoning = calculate_match_score(
            product, inv_item
        )

        if score >= min_score:
            match = InventoryMatch(
                inventory_item_number=inv_item.item_number,
                inventory_description=inv_item.raw_description,
                match_score=score,
                rank=1,  # Temporary, will be updated after sorting
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
