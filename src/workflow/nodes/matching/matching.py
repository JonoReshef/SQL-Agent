"""Workflow node for inventory matching"""

from typing import List

from sqlalchemy import select

from src.database.connection import get_db_session
from src.database.models import InventoryItem as DBInventoryItem
from src.models.inventory import InventoryItem as PydanticInventoryItem
from src.models.product import ProductProperty
from src.models.workflow import WorkflowState

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
                # Convert SQLAlchemy model to Pydantic model
                properties = [ProductProperty(**prop) for prop in db_item.properties]

                pydantic_item = PydanticInventoryItem(
                    item_number=db_item.item_number,
                    raw_description=db_item.raw_description,
                    exact_product_text=db_item.raw_description[:100],  # First 100 chars
                    product_name=db_item.product_name or "Unknown",
                    product_category=db_item.product_category or "Unknown",
                    properties=properties,
                    parse_confidence=db_item.parse_confidence or 0.0,
                    needs_manual_review=db_item.needs_manual_review or False,
                )

                inventory_items.append(pydantic_item)

    except Exception as e:
        # If database is not available or empty, return empty list
        # This allows the workflow to continue without inventory matching
        print(f"Warning: Could not load inventory from database: {e}")
        return []

    return inventory_items


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
    inventory_items = load_inventory_from_db()

    if not inventory_items:
        print("⚠️  No inventory items found in database")
        print("   Run 'python scripts/import_inventory.py' to populate inventory")
        state.errors.append("No inventory items available for matching")
        return state

    print(f"✅ Loaded {len(inventory_items)} inventory items")
    state.inventory_items = inventory_items

    # Match each product
    print(
        f"\n🔍 Matching {len(state.extracted_products)} products against inventory..."
    )

    product_matches = {}
    all_flags = []
    match_count = 0
    flag_count = 0

    for product in state.extracted_products:
        try:
            # Perform matching
            matches, flags = match_product_to_inventory(
                product=product,
                inventory_items=inventory_items,
                max_matches=3,
                min_score=0.5,
                review_threshold=0.7,
            )

            # Store matches
            if matches:
                product_matches[product.exact_product_text] = matches
                match_count += len(matches)

            # Collect flags
            all_flags.extend(flags)
            flag_count += len(flags)

        except Exception as e:
            error_msg = f"Error matching product '{product.exact_product_text}': {e}"
            print(f"   ⚠️  {error_msg}")
            state.errors.append(error_msg)
            continue

    # Update state
    state.product_matches = product_matches
    state.review_flags = all_flags

    # Print summary
    print(f"\n✅ Matching completed:")
    print(
        f"   Products matched: {len(product_matches)}/{len(state.extracted_products)}"
    )
    print(f"   Total matches: {match_count}")
    print(f"   Review flags: {flag_count}")

    return state
