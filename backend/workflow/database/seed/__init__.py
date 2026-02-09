"""Database seeding utilities for mock data generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workflow.database.seed.factories import (
        EmailFactory,
        InventoryItemFactory,
        InventoryMatchFactory,
        MockDataFactory,
        ProductMentionFactory,
        ReviewFlagFactory,
    )
    from workflow.database.seed.seed_database import seed_database

__all__ = [
    "seed_database",
    "MockDataFactory",
    "EmailFactory",
    "InventoryItemFactory",
    "ProductMentionFactory",
    "InventoryMatchFactory",
    "ReviewFlagFactory",
]


def __getattr__(name: str):
    """Lazy import to avoid circular imports when running as module."""
    if name == "seed_database":
        from workflow.database.seed.seed_database import seed_database

        return seed_database
    if name in (
        "MockDataFactory",
        "EmailFactory",
        "InventoryItemFactory",
        "ProductMentionFactory",
        "InventoryMatchFactory",
        "ReviewFlagFactory",
    ):
        from workflow.database.seed import factories

        return getattr(factories, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
