"""Product extraction workflow node"""

from typing import List
from src.models.workflow import WorkflowState
from src.models.product import ProductMention
from src.llm.extractors import extract_products_batch


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
        products: List[ProductMention] = extract_products_batch(state.emails)

        # Update state
        state.extracted_products = products

        return state

    except Exception as e:
        # Capture error and continue workflow
        state.errors.append(f"Extraction error: {str(e)}")
        return state
