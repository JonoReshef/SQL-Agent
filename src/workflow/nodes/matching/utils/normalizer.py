"""Property normalization for fuzzy matching"""

from typing import Dict, List, Tuple

from rapidfuzz import fuzz, process

from src.models.product import ProductProperty

# Common property value mappings for normalization
PROPERTY_NORMALIZATIONS: Dict[str, Dict[str, str]] = {
    "material": {
        "ss": "stainless steel",
        "s.s.": "stainless steel",
        "stainless": "stainless steel",
        "steel": "steel",
        "st steel": "stainless steel",
        "zinc": "zinc plated",
        "zn": "zinc plated",
        "zinc plated": "zinc plated",
        "galvanized": "galvanized",
        "galv": "galvanized",
    },
    "finish": {
        "zinc": "zinc plated",
        "zn": "zinc plated",
        "galv": "galvanized",
        "galvanized": "galvanized",
        "plain": "plain",
        "black": "black oxide",
        "black oxide": "black oxide",
    },
}

# Key terms to replace in property values if they appear
PROPERTY_REPLACEMENTS: Dict[str, Dict[str, str]] = {
    "pressure_rating": {
        "#": "lb",
        "lbs": "lb",
        "pound": "lb",
        "pounds": "lb",
        "rating": "lb",
    },
    "tpi": {
        "threads per inch": "TPI",
        "t.p.i.": "TPI",
        "tpi": "TPI",
    },
    "grade": {
        "gr": "grade",
    },
    "size": {"inch": '"'},
}


def find_matching_properties(
    source_props: List[ProductProperty],
    target_props: List[ProductProperty],
    min_similarity: float = 0.8,
) -> Tuple[List[str], List[str], Dict[str, float]]:
    """
    Find matching properties between two lists.

    Args:
        source_props: Source properties (e.g., from email)
        target_props: Target properties (e.g., from inventory)
        min_similarity: Minimum similarity threshold for a match

    Returns:
        Tuple of:
        - List of matched property names
        - List of missing property names (in source but not target)
        - Dictionary of property name to similarity score
    """
    matched = []
    missing = []
    scores = {}

    # Create lookup by property name
    target_by_name = {p.name.lower(): p for p in target_props}

    for source_prop in source_props:
        prop_name_lower = source_prop.name.lower()

        if prop_name_lower in target_by_name:
            target_prop = target_by_name[prop_name_lower]
            similarity = calculate_property_similarity(source_prop, target_prop)

            scores[source_prop.name] = similarity

            if similarity >= min_similarity:
                matched.append(source_prop.name)
            else:
                missing.append(source_prop.name)
        else:
            missing.append(source_prop.name)
            scores[source_prop.name] = 0.0

    return matched, missing, scores


def normalize_property_value(
    property: ProductProperty, fuzzy_threshold: int = 80
) -> str:
    """
    Normalize a property value for comparison.

    Uses hardcoded mappings first, then fuzzy matching for variations.

    Args:
        property_name: Name of the property (e.g., 'material', 'grade')
        value: Raw value to normalize
        fuzzy_threshold: Minimum similarity score for fuzzy matching (0-100)

    Returns:
        Normalized value
    """
    # Normalize to lowercase for comparison
    value_lower = property.value.lower().strip()
    property_lower = property.name.lower().strip()

    # Check if we have normalization rules for this property
    if property_lower in PROPERTY_NORMALIZATIONS:
        mapping = PROPERTY_NORMALIZATIONS[property_lower]

        # Direct match with normalization mapping
        if value_lower in mapping:
            return mapping[value_lower]

        # Fuzzy match against known values
        result = process.extractOne(
            value_lower,
            mapping.keys(),
            scorer=fuzz.ratio,
            score_cutoff=fuzzy_threshold,
        )

        if result:
            matched_key, score, _ = result
            return mapping[matched_key]

        # Check for replacements
    if property_lower in PROPERTY_REPLACEMENTS:
        replacements = PROPERTY_REPLACEMENTS[property_lower]

        # Direct match with replacement mapping
        for r in replacements.keys():
            if r.lower() in value_lower:
                value_lower = value_lower.replace(r, replacements[r])
                return value_lower.strip()

    # No normalization found - return cleaned original
    return property.value.strip()


def batch_normalize_properties(
    properties: List[ProductProperty], fuzzy_threshold: int = 80
) -> List[ProductProperty]:
    """
    Normalize a list of properties.

    Args:
        properties: List of ProductProperty objects
        fuzzy_threshold: Minimum similarity score for fuzzy matching

    Returns:
        List of ProductProperty objects with normalized values
    """
    normalized = []

    for prop in properties:
        normalized_value = normalize_property_value(prop, fuzzy_threshold)

        normalized.append(
            ProductProperty(
                name=prop.name,
                value=normalized_value,
                confidence=prop.confidence,
            )
        )

    return normalized


def calculate_property_similarity(
    prop1: ProductProperty, prop2: ProductProperty, normalize: bool = True
) -> float:
    """
    Calculate similarity between two properties.

    Args:
        prop1: First property
        prop2: Second property
        normalize: Whether to normalize values before comparison

    Returns:
        Similarity score (0.0 to 1.0)
    """
    # Properties must have same name to be comparable
    if prop1.name.lower() != prop2.name.lower():
        return 0.0

    # Normalize if requested
    value1 = prop1.value
    value2 = prop2.value

    # Only normalize non-measurement types
    if normalize:
        value1 = normalize_property_value(prop1)
        value2 = normalize_property_value(prop2)

    # Exact match
    if value1.lower() == value2.lower():
        return 1.0

    # For measurement types, require exact match
    if prop1.value_type == "measurement" or prop2.value_type == "measurement":
        # For measurements, require exact match after normalization
        return 0.0

    # Fuzzy match
    similarity = fuzz.ratio(value1.lower(), value2.lower()) / 100.0

    return similarity
