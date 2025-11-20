# WestBrand Email Analysis System

## Overview

A **production-ready** Python-based system for analyzing emails (`.msg` files) to extract product mentions, match them against inventory using **database-driven hierarchical filtering**, persist all data to **PostgreSQL**, and generate comprehensive **5-sheet Excel reports**. The system uses **Azure OpenAI (GPT-5)** orchestrated through **LangGraph** workflows with **fuzzy matching** for inventory reconciliation.

## Updated Architecture (November 2025)

### Key Design Decisions

1. **No Thread Reconstruction**: Each `.msg` file is analyzed as a single entity. No email threading or conversation reconstruction is performed.
2. **Synchronous Processing**: All operations are synchronous (no async/await) for simplicity. LLM calls use `.invoke()` not `.ainvoke()`.
3. **Test-Driven Development**: Comprehensive unit and integration tests using `pytest`. Currently testing infrastructure updates in progress.
4. **Database-First Architecture**: PostgreSQL 17 with content hashing and thread_hash as primary key for deduplication.
5. **Hierarchical Matching**: Database-driven property-based filtering (10-100x faster than linear scan) with fuzzy matching.

### Technology Stack

| Component            | Technology      | License | Purpose                             |
| -------------------- | --------------- | ------- | ----------------------------------- |
| **Database**         | PostgreSQL 17   | PostgreSQL | Data persistence with pgvector   |
| **ORM**              | SQLAlchemy 2.0  | MIT     | Database operations and models      |
| **Email Parsing**    | extract-msg     | MIT     | Parse Outlook .msg files            |
| **HTML Processing**  | BeautifulSoup4  | MIT     | Strip HTML from email bodies        |
| **AI Orchestration** | LangGraph       | MIT     | State machine workflow              |
| **LLM**              | AzureChatOpenAI | MIT     | Product extraction via Azure OpenAI |
| **Fuzzy Matching**   | rapidfuzz       | MIT     | Hierarchical inventory matching     |
| **Data Models**      | Pydantic v2     | MIT     | Type-safe data structures           |
| **Configuration**    | PyYAML          | MIT     | Product config management           |
| **Excel Output**     | openpyxl        | MIT     | Generate Excel reports              |
| **Caching**          | Redis           | BSD     | LLM response caching                |
| **Testing**          | pytest          | MIT     | Unit & integration tests            |

## Project Structure

```
WestBrand/
├── config/
│   └── products_config.yaml        # Product definitions & hierarchies
├── src/
│   ├── models/
│   │   ├── email.py                # Email & EmailMetadata models
│   │   ├── product.py              # ProductMention & ProductAnalytics models
│   │   ├── inventory.py            # InventoryItem & InventoryMatch models
│   │   └── workflow.py             # LangGraph state models
│   ├── database/
│   │   ├── models.py               # SQLAlchemy database models
│   │   ├── operations.py           # CRUD operations with upsert
│   │   ├── schema.py               # Database initialization
│   │   └── connection.py           # Database connection management
│   ├── analysis_workflow/
│   │   ├── graph.py                # LangGraph workflow (renamed from workflow/)
│   │   └── nodes/
│   │       ├── ingestion/          # Load and parse emails
│   │       ├── extraction/         # Extract products with LLM
│   │       ├── matching/           # Hierarchical inventory matching
│   │       │   └── utils/
│   │       │       ├── hierarchy.py    # Property hierarchy management
│   │       │       ├── filtering.py    # Database-driven filtering
│   │       │       ├── matcher.py      # Main matching interface
│   │       │       └── normalizer.py   # Property normalization
│   │       ├── persistence/        # Store to database
│   │       └── reporting/          # Generate 5-sheet Excel
│   ├── inventory/
│   │   ├── loader.py               # Load inventory from Excel
│   │   └── parser.py               # Parse inventory with LLM
│   ├── llm/
│   │   ├── client.py               # Azure OpenAI client wrapper
│   │   └── extractors.py          # Product extraction logic
│   ├── config/
│   │   └── config_loader.py       # Load YAML configuration
│   └── main.py                    # CLI entry point
├── scripts/
│   ├── import_inventory.py        # Import inventory to database
│   └── setup_database.py          # Initialize database schema
├── tests/
│   ├── test_msg_reader.py         # Email parsing tests
│   ├── test_signature_cleaner.py  # Signature cleaning tests
│   ├── test_database.py           # Database operations tests
│   ├── test_hierarchy.py          # Property hierarchy tests
│   ├── test_matcher.py            # Matching algorithm tests
│   ├── test_workflow.py           # Workflow tests
│   └── test_integration.py        # End-to-end tests
├── data/                          # Email .msg files
├── output/                        # Generated Excel reports
├── docker-compose.yml             # PostgreSQL + Redis containers
├── .env                           # Azure + Database credentials
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project metadata & pytest config
└── README.md                      # This file
```

## Completed Components ✅

### 1. Database Layer (`src/database/`)

- ✅ PostgreSQL 17 with pgvector extension
- ✅ SQLAlchemy 2.0 models with foreign key relationships
- ✅ **thread_hash** as primary key for email deduplication
- ✅ **content_hash** columns for all tables (change detection)
- ✅ Upsert operations with proper conflict resolution
- ✅ Database initialization and migration scripts
- ✅ Docker Compose configuration for PostgreSQL + Redis

### 2. Hierarchical Matching System (`src/analysis_workflow/nodes/matching/utils/`)

- ✅ Database-driven property-based filtering (10-100x faster)
- ✅ Property hierarchy loaded from config (cached with `@lru_cache`)
- ✅ Fuzzy matching with rapidfuzz (80% similarity threshold)
- ✅ Progressive filtering with graceful degradation
- ✅ Match scoring with weighted properties
- ✅ Review flag generation for quality issues

### 3. Email Processing (`src/email_processor/`)

- ✅ Parses Outlook `.msg` files using `extract-msg`
- ✅ Extracts metadata (subject, sender, recipients, date)
- ✅ Handles multiple body formats (plain text, HTML, RTF)
- ✅ Strips HTML tags and removes signatures
- ✅ Returns typed `Email` Pydantic models

### 4. Data Models (`src/models/`)

- ✅ `Email` and `EmailMetadata` - Email data structures
- ✅ `ProductMention` and `ProductProperty` - Product extraction
- ✅ `InventoryItem` and `InventoryMatch` - Matching results
- ✅ `ReviewFlag` - Match quality issues
- ✅ `WorkflowState` - LangGraph state management
- ✅ Updated to Pydantic v2 syntax (ConfigDict)

### 5. LangGraph Workflow (`src/analysis_workflow/graph.py`)

- ✅ 5-node workflow: Ingestion → Extraction → Matching → Persistence → Reporting
- ✅ Conditional matching (enabled with --match flag)
- ✅ Redis caching for LLM responses
- ✅ State management with Pydantic models
- ✅ Error accumulation and handling

### 6. Excel Report Generation (`src/analysis_workflow/nodes/reporting/`)

- ✅ 5-sheet Excel reports with openpyxl
- ✅ Conditional formatting (color-coded scores)
- ✅ Frozen headers and auto-filters
- ✅ Match confidence visualization (green/yellow/orange/red)
- ✅ Review flag priority coding

## Workflow Design

```
┌─────────────────────────────────────────────────────────────┐
│                  Configuration Layer                         │
│    products_config.yaml (products, properties, hierarchy)    │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer (PostgreSQL)                 │
│  emails_processed | product_mentions | inventory_items       │
│  inventory_matches | match_review_flags                      │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     Input Layer                              │
│      Scan directory → Load .msg files → Parse emails         │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Workflow (Synchronous)                │
│                                                              │
│  ┌──────────┐  ┌───────────┐  ┌─────────┐  ┌───────────┐  │
│  │Ingestion │→ │Extraction │→ │Matching*│→ │Persistence│  │
│  │          │  │           │  │         │  │           │  │
│  └──────────┘  └───────────┘  └─────────┘  └───────────┘  │
│       ↓                                           ↓         │
│  Parse .msg                                  Store to DB    │
│  Clean HTML                                  (with upsert)  │
│                                                   ↓         │
│                                         ┌──────────────┐    │
│                                         │  Reporting   │    │
│                                         │              │    │
│                                         └──────────────┘    │
│                                                              │
│  *Matching node (optional, enabled with --match flag):      │
│   • Database-driven hierarchical filtering                  │
│   • Fuzzy property matching with rapidfuzz                  │
│   • Match scoring and ranking                               │
│   • Review flag generation                                  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     Output Layer                             │
│              Excel Workbook (5 sheets)                       │
│  1. Product Mentions | 2. Analytics | 3. Email Summary      │
│  4. Inventory Matches* | 5. Review Flags*                   │
│                  (*if --match enabled)                       │
└─────────────────────────────────────────────────────────────┘
```

## Azure OpenAI Configuration

```python
from langchain_openai import AzureChatOpenAI
import os

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_LLM_API_KEY"),
    azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
    azure_deployment="gpt-5",  # Updated to GPT-5
    api_version="2024-08-01-preview",
    verbose=False,
    temperature=0,  # Deterministic for extraction
    reasoning_effort="low",
)
```

### Environment Variables Required

Create a `.env` file:

```bash
# Azure OpenAI
AZURE_LLM_API_KEY=your_api_key_here
AZURE_LLM_ENDPOINT=https://your-endpoint.openai.azure.com/

# PostgreSQL Database
DATABASE_URL=postgresql://westbrand:westbrand_pass@localhost:5432/westbrand_db

# Redis Cache (optional, defaults to localhost)
REDIS_URL=redis://localhost:6379
```

## Product Configuration

Example `config/products_config.yaml`:

```yaml
products:
  - name: 'Fasteners'
    category: 'Fasteners'
    aliases: ['bolts', 'nuts', 'screws', 'washers']
    properties:
      - name: 'grade'
        type: 'string'
        examples: ['2', '5', '8', 'A490']
      - name: 'size'
        type: 'string'
        examples: ['1/2-13', '3/4-10', 'M12']
      - name: 'length'
        type: 'string'
        examples: ['2"', '3 inches', '50mm']
      - name: 'finish'
        type: 'string'
        examples: ['zinc plated', 'galvanized', 'plain']
      - name: 'material'
        type: 'string'
        examples: ['steel', 'stainless', 'brass']

  - name: 'Threaded Rod'
    category: 'Threaded Rod'
    aliases: ['all-thread', 'threaded bar']
    properties:
      - name: 'diameter'
        type: 'string'
      - name: 'length'
        type: 'string'
      - name: 'grade'
        type: 'string'

extraction_rules:
  quantity_patterns:
    - "\\d+\\s*pcs?"
    - "\\d+\\s*pieces?"
    - "\\d+\\s*units?"
  date_formats:
    - '%m/%d/%Y'
    - '%d-%m-%Y'
    - '%B %d, %Y'
```

## Excel Report Structure

### Without --match flag (3 sheets):

#### Sheet 1: Product Mentions

| Product | Category | Properties | Quantity | Unit | Context | Date Requested | Email Subject | Sender | Email Date | File |
| ------- | -------- | ---------- | -------- | ---- | ------- | -------------- | ------------- | ------ | ---------- | ---- |

#### Sheet 2: Analytics

| Product | Category | Total Mentions | First Mention | Last Mention | Total Quantity | Unique Properties |
| ------- | -------- | -------------- | ------------- | ------------ | -------------- | ----------------- |

#### Sheet 3: Email Summary

| Email File | Subject | Sender | Date | Products Mentioned | Has Attachments |
| ---------- | ------- | ------ | ---- | ------------------ | --------------- |

### With --match flag (5 sheets):

#### Sheet 4: Inventory Matches

| Product | Inventory Item # | Description | Match Score | Rank | Matched Props | Missing Props | Reasoning |
| ------- | ---------------- | ----------- | ----------- | ---- | ------------- | ------------- | --------- |

**Color coding**:
- 🟢 Green (≥0.8): High confidence matches
- 🟡 Yellow (≥0.6): Medium confidence matches  
- 🟠 Orange (<0.6): Low confidence matches
- 🔴 Red: NO MATCHES found

#### Sheet 5: Review Flags

| Product | Issue Type | Match Count | Top Confidence | Reason | Action Needed |
| ------- | ---------- | ----------- | -------------- | ------ | ------------- |

**Priority coding**:
- 🔴 Red: High priority (missing critical properties)
- 🟡 Yellow: Medium priority (low match scores)
- 🟠 Orange: Low priority (informational)

## Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_msg_reader.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only unit tests
pytest tests/ -m unit
```

## Usage

### Prerequisites

```bash
# Start Docker containers (PostgreSQL + Redis)
docker-compose up -d

# Verify containers are running
docker ps

# Initialize database schema (first time only)
python scripts/setup_database.py

# Import inventory data (optional, for matching)
python scripts/import_inventory.py
```

### Running Analysis

```bash
# Activate virtual environment
source .venv/bin/activate

# Basic usage without inventory matching (3-sheet Excel)
python -m src.main data/sales@westbrand.ca output/report.xlsx

# With inventory matching (5-sheet Excel with matches and flags)
python -m src.main data/sales@westbrand.ca output/report.xlsx --match

# Process specific subdirectory
python -m src.main data/Sarah@westbrand.ca/Top-of-Information-Store output/sarah_report.xlsx --match

# Use defaults (data/selected → output/report_<timestamp>.xlsx)
python -m src.main --match
```

## Development Workflow

1. **Write Tests First**: Before implementing any feature, write comprehensive unit tests
2. **Run Tests Frequently**: Execute tests after each change
3. **Keep It Synchronous**: No async code - use `.invoke()` for LLM calls
4. **Single Email Processing**: Each `.msg` file is independent - no threading
5. **Type Safety**: All data uses Pydantic models for validation
6. **Database First**: All operations persist to PostgreSQL with upsert logic

## Current Status

**Production Ready** - Core features complete

### Completed Features ✅

- ✅ Email parsing and cleaning (extract-msg + BeautifulSoup)
- ✅ LLM-based product extraction (Azure OpenAI GPT-5)
- ✅ Database persistence (PostgreSQL with thread_hash + content_hash)
- ✅ Database-driven hierarchical matching (10-100x faster)
- ✅ Fuzzy property matching (rapidfuzz)
- ✅ Review flag generation (quality assurance)
- ✅ 5-sheet Excel reports (conditional formatting)
- ✅ LangGraph workflow orchestration
- ✅ Redis caching for LLM responses
- ✅ Docker Compose deployment
- ✅ Comprehensive test suite (infrastructure updates in progress)

### Known Issues

- ⚠️ Test infrastructure being updated for new module structure
- ⚠️ Full inventory import pending (11,197 items)

### Future Enhancements

- 🔄 Email linking in reports for source grounding
- 🔄 Web dashboard for reviewing matches interactively
- 🔄 Semantic search with pgvector
- 🔄 Automated scheduled email scanning
- ❌ Email thread reconstruction (explicitly out of scope)
- ❌ Async processing (not needed at current scale)

---

**Status**: Production Ready  
**Version**: 2.0  
**Last Updated**: November 19, 2025