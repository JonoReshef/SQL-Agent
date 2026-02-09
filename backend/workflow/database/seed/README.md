# Database Seeding

Generate mock data for local development.

## Quick Start

```bash
# Seed 1000 inventory items with related data
cd backend
uv run python -m workflow.database.seed.seed_database --count 1000

# Reset database and seed fresh
uv run python -m workflow.database.seed.seed_database --count 1000 --reset

# Seed specific categories only
uv run python -m workflow.database.seed.seed_database --categories fasteners,gaskets

# Preview without writing
uv run python -m workflow.database.seed.seed_database --dry-run

# Reproducible seeding
uv run python -m workflow.database.seed.seed_database --seed 42
```

## What Gets Created

| Table                | Approximate Count | Description                            |
| -------------------- | ----------------- | -------------------------------------- |
| `emails_processed`   | count / 3         | Email metadata with fake senders       |
| `inventory_items`    | count             | Products distributed across categories |
| `product_mentions`   | count             | Products extracted from emails         |
| `inventory_matches`  | count \* 3        | Match candidates per mention           |
| `match_review_flags` | count / 4         | Items needing review                   |

## Customizing Archetypes

Edit `archetypes.yaml` to add or modify product templates. Each category defines:

- `item_prefixes`: Item number patterns
- `product_names`: Valid product names
- `properties`: Property names with valid values

## PII Anonymization

All generated data uses fake values:

- Email addresses: `{first}.{last}@{fake_company}.example.com`
- Requestor names: Mimesis-generated names
- File paths: `/data/mock/...` prefix
- Company names: Synthetic industrial names

## API

```python
from workflow.database.seed import seed_database

# Seed programmatically
stats = seed_database(
    count=1000,
    categories=["fasteners", "gaskets"],
    reset=True,
    seed=42,
)

print(stats)
# {'emails': 333, 'inventory_items': 1000, ...}
```

## Factories

Individual factories can be used for custom data generation:

```python
from workflow.database.seed.factories import (
    EmailFactory,
    InventoryItemFactory,
    ProductMentionFactory,
    InventoryMatchFactory,
    ReviewFlagFactory,
)

# Create with reproducible seed
factory = InventoryItemFactory(seed=42)

# Generate single record
item = factory.create(category="fasteners", index=0)
print(item["item_number"])  # e.g., "B-0050-1234"
```
