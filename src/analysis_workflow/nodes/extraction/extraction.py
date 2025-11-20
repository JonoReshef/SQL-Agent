"""Product extraction workflow node"""

from typing import List

from models.analysis_workflow import WorkflowState
from src.database.operations import compute_content_hash
from src.llm.extractors import extract_products_batch
from src.models.product import ProductMention


def extract_products(state: WorkflowState) -> WorkflowState:
    """
    Extraction node: Extract product mentions from emails using LLM.

    Args:
        state: Current workflow state with emails list

    Returns:
        Updated state with extracted_products list populated
    """
    try:
        # Extract products from all emails
        raw_extracted_products: List[ProductMention] = extract_products_batch(state.emails)

        processed_products = process_products(raw_extracted_products)

        # Deduplicate products by properties to avoid redundant matching when there are only differences in quantities or price
        seen_properties = set()
        unique_property_products = []
        for product in processed_products:
            # Create a hashable representation of product properties
            property_key = compute_content_hash(product.properties)
            if property_key not in seen_properties:
                seen_properties.add(property_key)
                unique_property_products.append(product)

        print(
            f"   Identified {len(unique_property_products)} unique products from {len(processed_products)} total mentions."
        )

        # Update state
        state.extracted_products = processed_products
        state.unique_property_products = unique_property_products
        return state

    except Exception as e:
        # Capture error and continue workflow
        state.errors.append(f"Extraction error: {str(e)}")
        return state


def process_products(products: List[ProductMention]) -> List[ProductMention]:
    """
    Process extracted products based on business rules
    """

    # Remove all product mentions which mentioned "westbrand" in the email sender
    processed_products = [
        product
        for product in products
        if product.requestor is not None and "westbrand" not in product.requestor.lower()
    ]

    return processed_products
