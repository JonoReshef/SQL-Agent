#!/usr/bin/env python3
"""
Seed database with mock data for local development.

Usage:
    python -m workflow.database.seed.seed_database --count 1000 --reset
    python -m workflow.database.seed.seed_database --count 500 --categories fasteners,gaskets
    python -m workflow.database.seed.seed_database --dry-run
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from sqlalchemy import insert, text
from tqdm import tqdm

from workflow.database.connection import get_db_session, get_engine
from workflow.database.models import (
    EmailProcessed,
    InventoryItem,
    InventoryMatch,
    MatchReviewFlag,
    ProductMention,
    create_all_tables,
    drop_all_tables,
)
from workflow.database.seed.factories import (
    EmailFactory,
    InventoryItemFactory,
    InventoryMatchFactory,
    ProductMentionFactory,
    ReviewFlagFactory,
)

if TYPE_CHECKING:
    pass

CATEGORIES = [
    "fasteners",
    "gaskets",
    "nuts",
    "washers",
    "threaded_rod",
    "stud_kits",
    "casing_spacers",
]


def seed_database(
    count: int = 1000,
    categories: list[str] | None = None,
    reset: bool = False,
    dry_run: bool = False,
    seed: int | None = None,
) -> dict[str, int]:
    """
    Seed database with mock data.

    Args:
        count: Total number of inventory items to create
        categories: List of categories to seed (default: all)
        reset: Drop and recreate tables before seeding
        dry_run: Print stats without writing to database
        seed: Random seed for reproducibility

    Returns:
        Dictionary with seeding statistics
    """
    categories = categories or CATEGORIES
    items_per_category = count // len(categories)

    # Initialize factories
    email_factory = EmailFactory(seed=seed)
    inventory_factory = InventoryItemFactory(seed=seed)
    mention_factory = ProductMentionFactory(seed=seed)
    match_factory = InventoryMatchFactory(seed=seed)
    flag_factory = ReviewFlagFactory(seed=seed)

    stats = {
        "emails": 0,
        "inventory_items": 0,
        "product_mentions": 0,
        "inventory_matches": 0,
        "review_flags": 0,
    }

    if dry_run:
        print("DRY RUN: Would create approximately:")
        print(f"  - {count // 3} emails")
        print(f"  - {count} inventory items")
        print(f"  - {count} product mentions")
        print(f"  - {count * 3} inventory matches")
        print(f"  - {count // 4} review flags")
        return stats

    engine = get_engine()

    if reset:
        print("Dropping all tables...")
        drop_all_tables(engine)
        print("Creating tables...")
        create_all_tables(engine)

    with get_db_session() as session:
        # 1. Create emails (roughly 1 email per 3 products)
        num_emails = count // 3
        print(f"\nCreating {num_emails} emails...")
        emails = []
        for i in tqdm(range(num_emails), desc="Emails"):
            email_data = email_factory.create(i)
            emails.append(email_data)

        session.execute(insert(EmailProcessed), emails)
        stats["emails"] = len(emails)

        # 2. Create inventory items
        print(f"\nCreating {count} inventory items...")
        inventory_items = []
        for cat in categories:
            for i in tqdm(range(items_per_category), desc=f"Inventory ({cat})"):
                item_data = inventory_factory.create(cat, i)
                inventory_items.append(item_data)

        session.execute(insert(InventoryItem), inventory_items)
        session.flush()  # Get IDs

        # Query back IDs
        inv_ids = [
            row[0]
            for row in session.execute(
                text("SELECT id FROM inventory_items ORDER BY id DESC LIMIT :limit"),
                {"limit": len(inventory_items)},
            )
        ]
        stats["inventory_items"] = len(inventory_items)

        # 3. Create product mentions (1 per inventory item, linked to emails)
        print(f"\nCreating {count} product mentions...")
        mentions = []
        email_hashes = [e["thread_hash"] for e in emails]

        for i, cat in enumerate(categories):
            for j in tqdm(range(items_per_category), desc=f"Mentions ({cat})"):
                thread_hash = email_hashes[
                    (i * items_per_category + j) % len(email_hashes)
                ]
                mention_data = mention_factory.create(thread_hash, cat, j)
                mentions.append(mention_data)

        session.execute(insert(ProductMention), mentions)
        session.flush()

        mention_ids = [
            row[0]
            for row in session.execute(
                text("SELECT id FROM product_mentions ORDER BY id DESC LIMIT :limit"),
                {"limit": len(mentions)},
            )
        ]
        stats["product_mentions"] = len(mentions)

        # 4. Create inventory matches (3 per mention on average)
        print("\nCreating inventory matches...")
        matches = []
        for mention_id in tqdm(mention_ids, desc="Matches"):
            num_matches = email_factory.rng.randint(1, 5)
            sample_inv_ids = email_factory.rng.sample(
                inv_ids, min(num_matches, len(inv_ids))
            )

            for rank, inv_id in enumerate(sample_inv_ids, 1):
                match_data = match_factory.create(mention_id, inv_id, rank)
                matches.append(match_data)

        # Bulk insert in batches
        batch_size = 5000
        for i in range(0, len(matches), batch_size):
            batch = matches[i : i + batch_size]
            session.execute(insert(InventoryMatch), batch)
        stats["inventory_matches"] = len(matches)

        # 5. Create review flags (for ~25% of mentions)
        print("\nCreating review flags...")
        flags = []
        flagged_mentions = email_factory.rng.sample(mention_ids, len(mention_ids) // 4)

        for mention_id in tqdm(flagged_mentions, desc="Flags"):
            flag_data = flag_factory.create(mention_id)
            flags.append(flag_data)

        session.execute(insert(MatchReviewFlag), flags)
        stats["review_flags"] = len(flags)

        session.commit()

    print("\n=== Seeding Complete ===")
    for table, cnt in stats.items():
        print(f"  {table}: {cnt}")

    return stats


def main() -> None:
    """CLI entrypoint for database seeding."""
    parser = argparse.ArgumentParser(description="Seed database with mock data")
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Number of inventory items to create (default: 1000)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of categories (default: all)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before seeding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing to database",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    categories = args.categories.split(",") if args.categories else None

    seed_database(
        count=args.count,
        categories=categories,
        reset=args.reset,
        dry_run=args.dry_run,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
