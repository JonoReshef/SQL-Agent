"""Inventory description parser using LLM extraction"""

import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage

from src.llm.extractors import build_extraction_prompt, structured_llm
from src.models.email import Email, EmailMetadata
from src.models.inventory import InventoryItem
from src.models.product import ProductProperty


def parse_inventory_description(item_number: str, description: str) -> InventoryItem:
    """
    Parse inventory description to extract structured product information.

    Uses the same LLM extraction logic as email product extraction,
    treating the description as an email body.

    Args:
        item_number: Unique inventory item number
        description: Raw description text from inventory

    Returns:
        InventoryItem with extracted product information
    """
    # Create a mock email object for the extraction pipeline
    mock_email = Email(
        metadata=EmailMetadata(
            subject="Inventory Item",
            sender="inventory@system",
            recipients=["system@system"],
            message_id=f"<{item_number}>",
            cc=[],
            date=None,
        ),
        body=description,
        cleaned_body=description,  # Already clean
        attachments=[],
        file_path=None,
    )

    try:
        # Build extraction prompt
        prompt = build_extraction_prompt(mock_email)

        # Call LLM for extraction
        response = structured_llm.invoke([HumanMessage(content=prompt)])

        # Check if we got products
        if not response.products or len(response.products) == 0:
            # No products found - return with low confidence
            return InventoryItem(
                item_number=item_number,
                raw_description=description,
                exact_product_text=description[:100],  # First 100 chars
                product_name="Unknown",
                product_category="Unknown",
                properties=[],
                parse_confidence=0.0,
                needs_manual_review=True,
            )

        # Take the first extracted product (most relevant)
        extracted = response.products[0]

        # Calculate overall confidence
        if extracted.properties:
            avg_confidence = sum(p.confidence for p in extracted.properties) / len(
                extracted.properties
            )
        else:
            avg_confidence = 0.5  # Moderate confidence if no properties

        # Determine if manual review needed
        needs_review = (
            avg_confidence < 0.7  # Low confidence
            or len(extracted.properties) < 2  # Too few properties
            or not extracted.product_name  # Missing name
            or not extracted.product_category  # Missing category
        )

        # Create InventoryItem
        inventory_item = InventoryItem(
            item_number=item_number,
            raw_description=description,
            exact_product_text=extracted.exact_product_text,
            product_name=extracted.product_name,
            product_category=extracted.product_category,
            properties=extracted.properties,
            parse_confidence=avg_confidence,
            needs_manual_review=needs_review,
        )

        return inventory_item

    except Exception as e:
        # Error during extraction - flag for review
        return InventoryItem(
            item_number=item_number,
            raw_description=description,
            exact_product_text=description[:100],
            product_name="Error",
            product_category="Error",
            properties=[],
            parse_confidence=0.0,
            needs_manual_review=True,
        )


def parse_inventory_batch(
    inventory_items: List[dict],
) -> List[InventoryItem]:
    """
    Parse a batch of inventory items.

    Args:
        inventory_items: List of dicts with item_number and raw_description

    Returns:
        List of parsed InventoryItem objects
    """
    parsed_items = []

    for item in inventory_items:
        parsed = parse_inventory_description(
            item_number=item["item_number"],
            description=item["raw_description"],
        )
        parsed_items.append(parsed)

    return parsed_items
