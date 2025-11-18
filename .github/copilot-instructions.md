# WestBrand Email Analysis System - AI Agent Instructions

## System Overview

This is a **synchronous, test-driven Python system** that analyzes Outlook `.msg` emails to extract industrial product information, match them against inventory, persist data to PostgreSQL, and generate comprehensive Excel reports. The system uses **Azure OpenAI (GPT-5)** orchestrated through **LangGraph** workflows with **fuzzy matching** for inventory reconciliation.

## Key instructions

- Follow a test driven development, test-first approach by running and building unit tests as code is changed or created
- Update documentation and these instructions whenever there are material changes to the product
- When there are complex new capabilities created, make specific markdown instructions which can be referenced which explain how the system works and how to use it

### Core Architecture Principles

- **No async/await**: All operations are synchronous for simplicity. Use `llm.invoke()`, NOT `.ainvoke()`
- **No email threading**: Each `.msg` file is analyzed independently. Do NOT attempt thread reconstruction
- **Test-first approach**: Write tests before implementation. 128/129 tests currently passing (99.2%)
- **Type safety**: All data structures use Pydantic v2 models with strict validation
- **Database-first**: All emails, products, matches persist to PostgreSQL for historical analysis

## Critical Workflows

### Running the System

```bash
# Start Redis + PostgreSQL (required)
docker-compose up -d

# Run analysis without inventory matching (3-sheet Excel)
python -m src.main

# Run with inventory matching (5-sheet Excel)
python -m src.main --match

# Or with custom paths
python -m src.main data/custom/ output/report.xlsx --match
```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit              # Fast unit tests
pytest -m integration       # End-to-end tests
pytest -v                   # Verbose output

# Test configuration in pyproject.toml
```

### Environment Setup

Required variables in `.env`:

```bash
AZURE_LLM_API_KEY=<your-key>
AZURE_LLM_ENDPOINT=<your-endpoint>
DATABASE_URL=postgresql://westbrand:westbrand_pass@localhost:5432/westbrand_db
```

**Database**: PostgreSQL 17 with pgvector extension running in Docker (`westbrand-db` container)

LLM client is a **cached singleton** (`@lru_cache`) in `src/llm/client.py`. Configuration:

- Deployment: `gpt-5`
- API Version: `2024-08-01-preview`
- Temperature: 0 (deterministic)
- Reasoning effort: `low`

## LangGraph Workflow Architecture

### State Machine Flow

```
Ingestion Node → Extraction Node → Matching Node* → Persistence Node → Reporting Node
                                     (*conditional - only with --match flag)
```

**State structure** (`WorkflowState` Pydantic model):

```python
{
    "input_directory": str,
    "emails": List[Email],
    "extracted_products": List[ProductMention],
    "analytics": List[ProductAnalytics],
    "matching_enabled": bool,  # NEW: Set by --match flag
    "product_matches": List[InventoryMatch],  # NEW: Fuzzy matched products
    "review_flags": List[ReviewFlag],  # NEW: Match quality issues
    "report_path": str,
    "errors": List[str]  # Default: [] (auto-initialized)
}
```

### Node Responsibilities

- **Ingestion** (`src/workflow/nodes/ingestion.py`): Load `.msg` files, parse with `extract-msg`, clean signatures/HTML
- **Extraction** (`src/workflow/nodes/extraction.py`): Call Azure OpenAI to extract products using structured output
- **Matching** (`src/workflow/nodes/matching.py`): Fuzzy match extracted products to inventory using rapidfuzz, generate review flags
- **Persistence** (`src/workflow/nodes/persistence.py`): Store emails, products, matches, flags to PostgreSQL with upsert logic
- **Reporting** (`src/workflow/nodes/reporting.py`): Generate 3-sheet or 5-sheet Excel with openpyxl (conditional on matching)

**Redis caching** is enabled in `graph.py` via `langchain_redis.RedisCache` to reduce redundant LLM calls.
**PostgreSQL persistence** stores all workflow data via SQLAlchemy models in `src/database/models.py`.

## Data Models (Pydantic v2)

### Key Models Location: `src/models/`

```python
# email.py
EmailMetadata: message_id, subject, sender, recipients, cc, date
Email: metadata, body, cleaned_body, attachments, file_path

# product.py
ProductProperty: name, value, confidence
ProductMention: product_name, category, properties, quantity, unit, context, dates, email metadata
ProductAnalytics: aggregated metrics across mentions

# inventory.py (NEW)
InventoryItem: item_number, category, description, properties (grade, size, material, finish, length)
InventoryMatch: product mention → inventory item link with match_score, matched_properties
ReviewFlag: issue_type, description, priority (high/medium/low)

# workflow.py
WorkflowState: Pydantic BaseModel for LangGraph state management (with default values)
```

**Database Models**: `src/database/models.py` contains SQLAlchemy versions:

- `EmailProcessed`: file_path (PK), file_hash, subject, sender, date_sent
- `ProductMentionDB`: id (PK), email_id (FK), exact_product_text, category, properties JSON
- `InventoryItemDB`: id (PK), item_number (unique), category, description, properties JSON
- `InventoryMatchDB`: id (PK), product_mention_id (FK), inventory_item_id (FK), match_score, matched_properties JSON
- `MatchReviewFlagDB`: id (PK), product_mention_id (FK), issue_type, description, priority

**Important**: Use `model_dump()` and `ConfigDict` (Pydantic v2), NOT `dict()` or `Config` class.

## Product Configuration System

### `config/products_config.yaml`

Defines extractable products with:

- Product names and aliases (e.g., "Fasteners", "bolts", "nuts")
- Properties to extract (grade, size, material, finish, length)
- Examples for each property type

**Loading config**: Use `src/config/config_loader.py` which returns a `ProductsConfig` Pydantic model.

## Email Processing Pipeline

### Parsing: `src/email_processor/msg_reader.py`

- Uses `extract-msg` library (NOT `mail-parser`)
- Handles HTML, RTF, and plain text bodies
- Returns structured `Email` model
- **13 unit tests passing**

### Cleaning: `src/email_processor/signature_cleaner.py`

- Strips HTML with BeautifulSoup4
- Removes signatures, quoted replies (`>`), forwarded message headers
- Preserves core email content
- **13 unit tests passing**

**Critical**: Preprocessing dramatically improves LLM extraction accuracy. Always use `cleaned_body` over raw `body`.

## LLM Extraction Pattern

### Prompt Engineering (`src/llm/extractors.py`)

1. Loads product config definitions as JSON in prompt
2. Instructs LLM to extract **each product mention separately** (including duplicates with different properties)
3. Uses structured output via `llm.with_structured_output(ProductExtractionResult)`
4. Extracts: product text snippet, category, properties, quantity, unit, context, requestor, date

### Parallel Processing

Uses `ThreadPoolExecutor` with `tqdm` progress bar for batch email processing. Maintains synchronous pattern within threads.

## Excel Report Generation

### Output: `src/report/excel_generator.py`

**Without --match flag (3 sheets)**:

1. **Product Mentions**: Detailed per-mention data
2. **Analytics**: Aggregated metrics by product
3. **Email Summary**: Per-email metadata and product counts

**With --match flag (5 sheets)**:

4. **Inventory Matches**: Product → inventory mappings with color-coded match scores:
   - Green (≥0.8): High confidence
   - Yellow (≥0.6): Medium confidence
   - Orange (<0.6): Low confidence
   - Red: NO MATCHES found
5. **Review Flags**: Match quality issues with priority color coding:
   - Red: High priority (missing critical properties)
   - Yellow: Medium priority (low match scores)
   - Orange: Low priority (informational)

Features: Auto-filter, frozen panes, conditional formatting, date formatting, 60-char max column width

## Project-Specific Conventions

### File Organization

- **Models**: Always in `src/models/` with clear separation (email, product, workflow)
- **Tests**: Mirror `src/` structure in `tests/` directory
- **Fixtures**: Real `.msg` files in `tests/fixtures/` for integration testing
- **Data**: Production emails in `data/` subdirectories (organized by source mailbox)

### Testing Patterns

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # End-to-end workflow tests
@pytest.mark.ai          # LLM-dependent tests
```

### Error Handling

- Accumulate errors in `WorkflowState["errors"]` list
- Continue processing remaining emails on individual failures
- Log errors but don't halt workflow
- Report all errors at end of execution

### Code Style

- Type hints on all functions
- Docstrings with Args/Returns sections
- Prefer explicit over implicit (e.g., `cleaned_body if cleaned_body else body`)
- Use `Path` objects for file operations

## Database Operations

### Persistence Layer: `src/database/operations.py`

**Critical**: All text fields must be sanitized with `sanitize_for_db()` to remove NUL bytes (`\x00`) before insertion.

```python
def sanitize_for_db(text: str | None) -> str | None:
    """Remove NUL bytes that cause PostgreSQL DataError"""
    if text is None:
        return None
    return text.replace("\x00", "")
```

**Upsert Functions** (all return `{"inserted": int, "updated": int, "errors": [str]}`):

1. **store_emails(emails)**: Upserts to `emails_processed` using `file_path` as natural key, calculates SHA256 `file_hash`
2. **store_product_mentions(products, emails)**: Links to emails via `email_id` FK, requires email list for path-to-ID lookup
3. **store_inventory_matches(matches, products, items)**: Links via `product_mention_id` and `inventory_item_id` FKs
4. **store_review_flags(flags, products)**: Links via `product_mention_id` FK

**Foreign Key Handling**: Functions build lookup maps first (e.g., `email_path_to_id`, `product_text_to_id`) to resolve IDs efficiently.

**Error Handling**: Duplicate key errors are expected and handled gracefully (e.g., same product text in same email).

### Database Schema: `src/database/schema.py`

```python
from src.database.schema import init_database
init_database()  # Creates all tables if not exist
```

**Schema Features**:

- Foreign key constraints with `ondelete="CASCADE"`
- JSON columns for flexible property storage
- Unique constraints on natural keys (file_path, item_number)
- Indexes on foreign keys for query performance

### Inventory Import: `scripts/import_inventory.py`

```bash
# Import all items (11,197 items)
python scripts/import_inventory.py

# Import limited items for testing
python scripts/import_inventory.py --max-items 50
```

**Process**: Reads Excel → LLM parses properties → Stores to `inventory_items` table with upsert on `item_number`.

## Inventory Matching System

### Hierarchical Filtering Engine: `src/matching/` and `src/database/filtering.py`

**NEW Architecture** (as of November 2025): The system uses **database-driven hierarchical property-based filtering** for drastically improved performance and accuracy with large inventory datasets (10k-100k items).

**IMPORTANT**: To avoid circular imports, the `filter_inventory_by_hierarchical_properties` function has been **moved to `src/database/filtering.py`** (separate from `operations.py`). The `src/matching/__init__.py` does NOT expose matcher functions at package level - always import directly:

```python
# ✅ CORRECT - Direct import
from src.matching.matcher import match_product_to_inventory
from src.database.filtering import filter_inventory_by_hierarchical_properties

# ❌ WRONG - Package-level import (circular dependency)
from src.matching import match_product_to_inventory  # This will fail!
```

#### Core Modules:

1. **hierarchy.py**: Loads property hierarchies from `config/products_config.yaml`

   - `PropertyHierarchy`: Stores ordered list of properties for each category
   - `get_hierarchy_for_category()`: Cached function to load hierarchies
   - Property order defines filtering priority (e.g., Fasteners: grade → size → length → material → finish)

2. **filtering.py** (in `src/database/`): Database-driven filtering (NEW - extracted to break circular imports)

   - `filter_inventory_by_hierarchical_properties()`: Executes hierarchical filtering as PostgreSQL queries
   - Progressive filtering with threshold logic (continues if ≥10 items, stops if <10)
   - Uses fuzzy matching via `normalizer.py` for property value variations
   - Returns filtered items and filter depth for analysis

3. **filter.py**: DEPRECATED - Old in-memory filtering (kept for backward compatibility)

   - `filter_by_property()`: Single property filter (DEPRECATED - use database filtering)
   - `hierarchical_filter()`: In-memory progressive filtering (DEPRECATED)
   - `score_filtered_items()`: Scoring logic (DEPRECATED)
   - All functions emit deprecation warnings
   - Kept only for unit tests and backward compatibility

4. **matcher.py**: Main matching interface (uses database filtering)

   - `match_product_to_inventory()`: Returns (matches, review_flags) - uses database filtering internally
   - `find_best_matches()`: Uses `filter_inventory_by_hierarchical_properties()` from `database.filtering` module
   - `calculate_match_score()`: Weighted scoring (40% name, 20% category, 40% properties)

5. **normalizer.py**: Property value normalization
   - Handles variations: "gr8" → "8", "ss" → "stainless steel", "galv" → "galvanized"
   - Uses `rapidfuzz` for fuzzy matching with 80% similarity threshold
   - Batch normalization for performance

#### How Database-Driven Hierarchical Matching Works:

```python
# Example: Matching "1/2-13 x 2" Grade 8 Hex Bolt"
#
# Inventory: 11,197 items in PostgreSQL
#
# Database Query 1: Filter by category='Fasteners' → ~5,000 items
# Database Query 2: Filter by grade=8 → ~1,200 items (with fuzzy matching)
# Database Query 3: Filter by size=1/2-13 → ~150 items (80x reduction)
# Database Query 4: Filter by length=2" → ~20 items (560x reduction)
#
# Result: Score and rank only 20 candidates instead of 11,197
# Performance: 10-100x faster than in-memory approach
```

**Key Benefits**:

- **10-100x performance improvement** over in-memory linear scan
- **Scalable**: Handles 100k+ inventory items efficiently
- **Better accuracy**: Respects domain knowledge (grade more important than finish)
- **Graceful degradation**: Returns broader matches if narrow filter yields nothing (threshold=10)
- **Config-driven**: Hierarchy defined in YAML, no code changes needed
- **Indexed**: Uses GIN index on JSON properties column for fast lookups

#### Database Schema:

```sql
-- inventory_items table
CREATE TABLE inventory_items (
    id SERIAL PRIMARY KEY,
    item_number VARCHAR(100) UNIQUE NOT NULL,
    raw_description TEXT NOT NULL,
    product_name VARCHAR(255),
    product_category VARCHAR(255),
    properties JSONB NOT NULL,  -- [{"name": "grade", "value": "8", "confidence": 1.0}]
    content_hash VARCHAR(64) NOT NULL,
    parse_confidence FLOAT,
    needs_manual_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- GIN index for fast JSON property lookups
CREATE INDEX idx_inventory_properties ON inventory_items USING gin(properties jsonb_path_ops);
```

#### Property Normalization Examples:

```python
# Grade: "Grade 8" → "8", "gr8" → "8", "A490" → "a490"
# Size: "1/2-13" → "1/2-13", "1/2 inch" → "1/2", "M12" → "m12"
# Finish: "zinc plated" → "zinc", "galvanized" → "galv", "plain" → "plain"
```

#### Review Flag Generation:

Auto-generated for:

- **No matches found** (INSUFFICIENT_DATA)
- **Low match scores** (<0.7 threshold)
- **Ambiguous matches** (top 2 scores differ by <0.1)
- **Missing critical properties** (≥2 properties not in inventory)

#### Testing:

- **14 tests** for database hierarchical filtering (all passing) - `test_database_hierarchical_filtering.py`
- **12 tests** for old in-memory filtering (all passing, deprecated) - `test_hierarchical_filter.py`
- **10 tests** for matcher integration (all passing) - `test_matcher.py`
- **Test files**: `test_hierarchy.py`, `test_database_hierarchical_filtering.py`, `test_matcher.py`

## Common Pitfalls to Avoid

1. **Don't use async**: This codebase is intentionally synchronous
2. **Don't attempt email threading**: Out of scope by design
3. **Don't skip preprocessing**: HTML removal is critical for LLM accuracy
4. **Don't modify product config without updating extractors**: Config and prompts are tightly coupled
5. **Don't forget Docker containers**: Both Redis AND PostgreSQL must be running (`docker-compose up -d`)
6. **Don't use old Pydantic syntax**: This is v2 (use `ConfigDict`, not `Config`)
7. **Don't insert text without sanitization**: Always use `sanitize_for_db()` to remove NUL bytes before database operations
8. **Don't assume unique product mentions**: Same product text in same email creates duplicates (expected behavior)
9. **Don't forget to pass context to store functions**: `store_product_mentions()` needs emails list, `store_inventory_matches()` needs products + items lists

## Integration Points

### External Dependencies

- **Azure OpenAI**: All LLM calls go through `get_llm_client()` singleton
- **Redis**: Required for LangChain caching (`redis://localhost:6379`)
- **PostgreSQL 17**: Primary data store with pgvector extension (`localhost:5432`)
- **LangGraph**: State management and workflow orchestration
- **rapidfuzz**: Fuzzy string matching for inventory reconciliation

### Data Flow

```
.msg files → extract-msg → BeautifulSoup (cleaning) →
LangGraph state → Azure OpenAI (structured output) →
Pydantic models → rapidfuzz (matching)* → SQLAlchemy (database) →
openpyxl → Excel report (3 or 5 sheets)

*matching step only runs with --match flag
```

## Debugging Tips

- Check Docker containers running: `docker ps` should show `westbrand-redis` AND `westbrand-db`
- Validate `.env` variables: `echo $AZURE_LLM_API_KEY` and `echo $DATABASE_URL`
- Query database directly: `docker exec -it westbrand-db psql -U westbrand -d westbrand_db`
- Check table counts: `SELECT COUNT(*) FROM emails_processed;` (repeat for other tables)
- Run single tests: `pytest tests/test_extractors.py::TestClassName::test_method -v`
- Inspect LangGraph state: Add print statements in node functions
- Check LLM responses: Set `verbose=True` in `client.py` temporarily
- Debug matching: Set breakpoint in `src/inventory/matcher.py` to inspect scores
- Check NUL byte issues: Search logs for "DataError" or "invalid byte sequence"

## Completed Features (as of v2.0)

✅ Database persistence (PostgreSQL with SQLAlchemy)
✅ Inventory matching (rapidfuzz fuzzy matching)
✅ Review flag generation (match quality issues)
✅ 5-sheet Excel reports (with conditional formatting)
✅ 128/129 tests passing (99.2% coverage)

## Future Considerations

- Email linking in reports for source grounding (clickable .msg file paths)
- Better email export formats from Outlook/Gmail (currently .msg only)
- Unique product extraction per email thread (currently extracts all mentions as separate records)
- Async processing for large-scale deployments (if needed for performance)
- Web dashboard for reviewing matches and flagged items interactively
- Automated workflows with scheduled email scanning
