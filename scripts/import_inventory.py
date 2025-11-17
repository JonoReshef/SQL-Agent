#!/usr/bin/env python3
"""
Import inventory from Excel file into PostgreSQL database.

This script:
1. Loads Item List.xlsx from data/Inventory/
2. Parses each description using LLM extraction
3. Upserts inventory items to database (insert or update based on item_number)
4. Shows progress with statistics
"""

import sys
from pathlib import Path

from sqlalchemy import select
from tqdm import tqdm

from src.database.connection import get_db_session, test_connection
from src.database.models import InventoryItem as DBInventoryItem
from src.database.operations import compute_content_hash
from src.inventory.loader import get_inventory_stats, load_inventory_excel
from src.inventory.parser import parse_inventory_batch


def import_inventory(
    excel_path: str | Path = "data/Inventory/Item List.xlsx",
    max_items: int | None = None,
) -> dict:
    """
    Import inventory from Excel file to database.

    Args:
        excel_path: Path to inventory Excel file
        max_items: Maximum number of items to import (None = import all)

    Returns:
        Dictionary with import statistics
    """
    excel_path = Path(excel_path)

    # Validate database connection
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed")
        return {"success": False, "error": "Database connection failed"}

    # Load Excel file
    print(f"\n📂 Loading inventory from {excel_path}...")
    try:
        raw_items = load_inventory_excel(excel_path)
    except Exception as e:
        print(f"❌ Failed to load Excel: {e}")
        return {"success": False, "error": str(e)}

    print(f"✅ Loaded {len(raw_items)} items from Excel")

    # Limit items if max_items is specified
    if max_items is not None:
        raw_items = raw_items[:max_items]
        print(f"🔢 Limited to first {len(raw_items)} items for import")

    # Show statistics
    stats = get_inventory_stats(raw_items)
    print("\n📊 Inventory Statistics:")
    print(f"   Total Items: {stats['total_items']}")
    print(f"   Avg Description Length: {stats['avg_description_length']}")

    # Parse descriptions using LLM
    print("\n🤖 Parsing descriptions with LLM...")
    print(f"   Note: This may take several minutes for {len(raw_items)} items")
    try:
        parsed_items = parse_inventory_batch(raw_items)
    except Exception as e:
        print(f"❌ Failed to parse descriptions: {e}")
        return {"success": False, "error": f"Parsing failed: {e}"}

    print(f"✅ Parsed {len(parsed_items)} items")

    # Upsert to database
    print(f"\n💾 Upserting to database...")
    inserted_count = 0
    updated_count = 0
    error_count = 0
    errors = []

    with get_db_session() as session:
        for item in tqdm(parsed_items, desc="Importing", unit="item"):
            try:
                # Check if item exists
                stmt = select(DBInventoryItem).where(
                    DBInventoryItem.item_number == item.item_number
                )
                existing = session.execute(stmt).scalar_one_or_none()

                # Assumes that an inventory number is always unique and immutable (ie once created parts do not change)
                if not existing:
                    # Compute content hash for comparison
                    # Compute content hash for new item
                    properties_json = [prop.model_dump() for prop in item.properties]
                    content_hash = compute_content_hash(item)

                    # Insert new item
                    db_item = DBInventoryItem(
                        item_number=item.item_number,
                        raw_description=item.raw_description,
                        product_name=item.product_name,
                        product_category=item.product_category,
                        properties=properties_json,
                        parse_confidence=item.parse_confidence,
                        needs_manual_review=item.needs_manual_review,
                        content_hash=content_hash,
                    )
                    session.add(db_item)
                    inserted_count += 1
                else:
                    content_hash = compute_content_hash(item)
                    existing_hash = str(existing.content_hash)
                    if existing_hash != content_hash:
                        print(
                            f"Existing item found for {item.item_number} with different properties. This is a data quality issue"
                        )

                # Commit every 100 items to avoid large transactions
                if (inserted_count + updated_count) % 100 == 0:
                    session.commit()

            except Exception as e:
                error_count += 1
                errors.append(f"Item {item.item_number}: {e}")
                session.rollback()
                continue

        # Final commit
        try:
            session.commit()
        except Exception as e:
            print(f"❌ Failed to commit final batch: {e}")
            session.rollback()
            return {
                "success": False,
                "error": f"Final commit failed: {e}",
                "inserted": inserted_count,
                "updated": updated_count,
                "errors": error_count,
            }

    # Print summary
    print(f"\n✅ Import completed!")
    print(f"   Inserted: {inserted_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Errors: {error_count}")

    if errors:
        print(f"\n⚠️  Errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more")

    return {
        "success": True,
        "inserted": inserted_count,
        "updated": updated_count,
        "errors": error_count,
        "error_details": errors,
        "total_processed": inserted_count + updated_count,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import inventory from Excel to database"
    )
    parser.add_argument(
        "--file",
        "-f",
        default="data/Inventory/Item List.xlsx",
        help="Path to inventory Excel file (default: data/Inventory/Item List.xlsx)",
    )
    parser.add_argument(
        "--max-items",
        "-n",
        type=int,
        default=None,
        help="Maximum number of items to import (default: None = import all)",
    )

    args = parser.parse_args()

    result = import_inventory(args.file, max_items=args.max_items)

    if not result["success"]:
        sys.exit(1)
