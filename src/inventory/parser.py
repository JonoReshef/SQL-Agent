"""Inventory description parser using LLM extraction"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from tqdm import tqdm

from src.config.config_loader import load_config
from src.llm.client import get_llm_client

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage

from src.models.inventory import InventoryItem
from src.models.product import ProductItemResult

structured_llm = get_llm_client(
    type="gpt4.1",
    output_structure=ProductItemResult,
)


def parse_inventory_description(
    item_numbers: list[str], descriptions: list[str]
) -> tuple[list[InventoryItem], list[str]]:
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

    try:
        # Build extraction prompt
        prompt = """
        You are an expert and analyzing and categorizing inventory items based on product descriptions. You will receive a list of {count_items} inventory items. Process all {count_items} items. For each item extract the following details:

        1. exact_product_text: The full free text snippet that is describing the product.
        2. product_id: The unique identifier of the product which will be supplied alongside the description.
        3. product_name: The name of the product. 
        4. product_category: The category of the product. 
        5. properties: A list of properties with name, value, and confidence score.

        Output the results as a list of objects in the following format:
        [
            {{
                "exact_product_text": str,
                "product_id": str,
                "product_name": str,
                "product_category": str,
                "properties": [
                    {{
                        "name": str,
                        "value": str,
                        "confidence": float (0.0 to 1.0)
                    }}
                ]
            }}
        ]

        Below are the key product types to search for in the emails. They include examples of the product configurations which should help identify relevant products in the email. Do not use these values directly, only use them to guide extraction.

        PRODUCT DEFINITIONS:
        {product_definitions}

        Below are the inventory descriptions to extract products from:
        {descriptions}
        """

        # Call LLM for extraction
        response: ProductItemResult = structured_llm.invoke(
            [
                HumanMessage(
                    content=prompt.format(
                        count_items=len(item_numbers),
                        product_definitions=load_config(),
                        descriptions=[
                            f"product_id: {item_number}: exact_product_text: {description}"
                            for item_number, description in zip(
                                item_numbers, descriptions
                            )
                        ],
                    )
                )
            ]
        )  # type: ignore

        inventory_items = []
        unextracted_items = item_numbers.copy()

        for item in response.items:
            if item.product_id is None:
                continue
            if item.product_id not in item_numbers:
                continue
            if item.exact_product_text not in descriptions:
                continue

            # Average confidence is the mean of all property confidences
            avg_confidence = (
                sum(prop.confidence for prop in item.properties) / len(item.properties)
                if item.properties
                else 0.0
            )

            # Requires manual review if avg confidence < 0.7 or any property < 0.5 or no properties extracted
            needs_review = (
                avg_confidence < 0.7
                or len(item.properties) == 0
                or any(prop.confidence < 0.5 for prop in item.properties)
            )

            # Create InventoryItem
            inventory_item = InventoryItem(
                item_number=item.product_id,
                product_id=item.product_id,
                raw_description=item.exact_product_text,
                exact_product_text=item.exact_product_text,
                product_name=item.product_name,
                product_category=item.product_category,
                properties=item.properties,
                parse_confidence=avg_confidence,
                needs_manual_review=needs_review,
            )
            inventory_items.append(inventory_item)
            unextracted_items.remove(item.product_id)

        return inventory_items, unextracted_items

    except Exception as e:
        # Error during extraction - flag for review
        print(f"Error parsing inventory descriptions: {e}")
        return [], item_numbers


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
    batch_size = 50
    total_items = 200
    inventory_items_processing = inventory_items.copy()[:total_items]

    with tqdm(total=total_items) as pbar:
        while len(inventory_items_processing) > 0:
            batch = inventory_items_processing[:batch_size]
            item_numbers = [item["item_number"] for item in batch]
            descriptions = [item["raw_description"] for item in batch]

            parsed_batch, _ = parse_inventory_description(item_numbers, descriptions)
            extracted_items = [p.product_id for p in parsed_batch]

            inventory_items_processing = [
                item
                for item in inventory_items_processing
                if item["item_number"] not in extracted_items
            ]
            parsed_items.extend(parsed_batch)
            pbar.update(
                len(parsed_batch),
            )

    return parsed_items
