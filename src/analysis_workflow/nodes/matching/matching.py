"""Workflow node for inventory matching"""

from multiprocessing import Pool, cpu_count
from typing import List

from sqlalchemy import select
from tqdm import tqdm

from src.database.connection import get_db_session
from src.database.models import InventoryItem as DBInventoryItem
from src.models.analysis_workflow import WorkflowState
from src.models.inventory import InventoryItem as PydanticInventoryItem
from src.utils.compute_content_hash import compute_content_hash

from .utils.matcher import match_product_to_inventory


def load_inventory_from_db() -> List[PydanticInventoryItem]:
    """
    Load all inventory items from database.

    Returns:
        List of InventoryItem Pydantic models
    """
    inventory_items = []

    try:
        with get_db_session() as session:
            stmt = select(DBInventoryItem).order_by(DBInventoryItem.item_number)
            results = session.execute(stmt).scalars().all()

            for db_item in results:
                # Convert SQLAlchemy model to dict, then validate as Pydantic model
                # Properties are already stored as list of dicts in JSON column
                pydantic_item = PydanticInventoryItem.model_validate(
                    {
                        "item_number": db_item.item_number,
                        "product_id": db_item.item_number,
                        "raw_description": db_item.raw_description,
                        "exact_product_text": db_item.raw_description,
                        "product_name": db_item.product_name or "",
                        "product_category": db_item.product_category or "Unknown",
                        "properties": db_item.properties,  # Already list of dicts with name/value/confidence
                        "parse_confidence": db_item.parse_confidence or 1.0,
                        "needs_manual_review": db_item.needs_manual_review or False,
                    }
                )

                inventory_items.append(pydantic_item)

    except Exception as e:
        # If database is not available or empty, return empty list
        # This allows the workflow to continue without inventory matching
        print(f"Warning: Could not load inventory from database: {e}")
        return []

    return inventory_items


def process_product_match(product):
    """
    Process a single product match.

    Args:
        product: Product to match

    Returns:
        Tuple of (product_hash, matches, flags, error_msg)
    """
    try:
        matches, flags = match_product_to_inventory(
            product=product,
            max_matches=3,
            min_score=0.5,
            review_threshold=0.7,
        )

        product_hash = compute_content_hash(product) if matches else None
        return (product_hash, matches, flags, None)

    except Exception as e:
        error_msg = f"Error matching product '{product.exact_product_text}': {e}"
        return (None, [], [], error_msg)


def match_products(state: WorkflowState) -> WorkflowState:
    """
    Match extracted products against inventory items.

    This node:
    1. Loads inventory items from database
    2. Matches each product against inventory
    3. Generates review flags for low-confidence or problematic matches
    4. Updates state with matches and flags

    Args:
        state: Current workflow state with extracted products

    Returns:
        Updated workflow state with inventory matches and review flags
    """
    # Check if matching is enabled
    if not state.matching_enabled:
        print("Inventory matching disabled, skipping...")
        return state

    # Load inventory from database
    print("\n📦 Loading inventory from database...")

    # Match each product
    print(f"\n🔍 Matching {len(state.extracted_products)} products against inventory...")

    product_matches = {}
    all_flags = []
    match_count = 0
    flag_count = 0

    # Prepare for parallel processing

    # Use multiprocessing Pool
    num_workers = min(cpu_count() - 2, len(state.unique_property_products))

    with Pool(processes=num_workers) as pool:
        results = list(
            tqdm(
                pool.imap(process_product_match, state.unique_property_products),
                total=len(state.unique_property_products),
                desc="Matching products",
            )
        )

    # Collect results
    for product_hash, matches, flags, error_msg in results:
        if error_msg:
            print(f"   ⚠️  {error_msg}")
            state.errors.append(error_msg)
            continue

        if matches and product_hash:
            product_matches[product_hash] = matches
            match_count += len(matches)

        all_flags.extend(flags)
        flag_count += len(flags)

    # Update state
    state.product_matches = product_matches
    state.review_flags = all_flags

    # Print summary
    print("\n✅ Matching completed:")
    print(f"   Products matched: {len(product_matches)}/{len(state.extracted_products)}")
    print(f"   Total matches: {match_count}")
    print(f"   Review flags: {flag_count}")

    return state
