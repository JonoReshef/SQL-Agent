# WestBrand Email Analysis - Architectural Overview

## Executive Summary

A test-driven Python system for analyzing Outlook emails to extract product information, match against inventory using **database-driven hierarchical filtering**, and generate comprehensive 5-sheet Excel reports with full database persistence. The system processes individual `.msg` files (no threading), uses Azure OpenAI (GPT-5) for intelligent extraction, PostgreSQL 17 with **thread_hash** as primary key for deduplication, and is orchestrated via LangGraph workflows.

**Key Features**:

- Synchronous email analysis with LLM extraction
- PostgreSQL database with thread_hash PKs and content_hash for all records
- Database-driven hierarchical matching (10-100x faster than linear scan)
- Fuzzy property matching using rapidfuzz
- Multi-sheet Excel reports (3 or 5 sheets based on --match flag)
- Production-ready deployment with Docker Compose

## Core Architectural Principles

### 1. Simplicity First

- **Synchronous Processing**: No async/await complexity
- **Single Email Analysis**: Each `.msg` file processed independently
- **No Thread Reconstruction**: Explicitly avoided - too complex and outside scope
- **Clear Data Flow**: Input → Process → Output

### 2. Test-Driven Development

- **Tests Before Code**: Write comprehensive tests first
- **Continuous Validation**: Run tests frequently during development
- **26/26 Tests Passing**: Strong foundation established
- **Pytest Framework**: Modern, well-documented testing

### 3. Type Safety

- **Pydantic v2**: All data structures typed and validated
- **Compile-time Checks**: Catch errors early
- **Self-documenting**: Models serve as API documentation

### 4. Database-Backed Persistence

- **PostgreSQL with pgvector**: Relational database for structured data
- **Foreign Key Relationships**: Proper data integrity
- **Upsert Operations**: Idempotent database writes
- **Optional Database**: System works without database if needed

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYER                         │
│                   (products_config.yaml)                        │
│                                                                 │
│  • Product Definitions (Fasteners, Threaded Rod, etc.)         │
│  • Properties to Extract (grade, size, material, etc.)         │
│  • Extraction Rules (patterns, formats)                        │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                              │
│                  (PostgreSQL 17 + pgvector)                     │
│                                                                 │
│  Tables:                                                        │
│  • emails_processed                                            │
│    - thread_hash VARCHAR(64) PRIMARY KEY (SHA256 content hash) │
│    - file_path, subject, sender, date_sent                     │
│  • product_mentions                                            │
│    - id SERIAL PRIMARY KEY                                      │
│    - email_thread_hash FK → emails_processed.thread_hash       │
│    - content_hash VARCHAR(64) (for change detection)           │
│  • inventory_items                                             │
│    - id SERIAL PRIMARY KEY                                      │
│    - item_number VARCHAR(100) UNIQUE                           │
│    - content_hash VARCHAR(64) (for change detection)           │
│  • inventory_matches                                           │
│    - id SERIAL PRIMARY KEY                                      │
│    - product_mention_id FK → product_mentions.id              │
│    - inventory_item_id FK → inventory_items.id                │
│    - content_hash VARCHAR(64) (for change detection)           │
│  • match_review_flags                                          │
│    - id SERIAL PRIMARY KEY                                      │
│    - product_mention_id FK → product_mentions.id              │
│    - content_hash VARCHAR(64) (for change detection)           │
│                                                                 │
│  Features:                                                      │
│  • Foreign key constraints with CASCADE deletes                 │
│  • Indexes on all FKs and content_hash columns                  │
│  • Upsert operations based on natural keys                      │
│  • Content hashing for intelligent change detection             │
│  • Docker Compose for easy deployment                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                       INPUT PIPELINE                            │
│                                                                 │
│  Directory Scanner → .msg File Discovery → Email Parser         │
│                                                                 │
│  ✅ Implemented:                                                │
│    • read_msg_file(path) - Parse single email                  │
│    • read_msg_files_from_directory(dir) - Batch parse          │
│    • Extract metadata (subject, sender, recipients, date)      │
│    • Extract body (HTML, RTF, plain text)                      │
│    • List attachments                                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                  PREPROCESSING PIPELINE                         │
│                                                                 │
│  HTML Stripping → Signature Removal → Text Cleaning            │
│                                                                 │
│  ✅ Implemented:                                                │
│    • strip_html_tags() - BeautifulSoup HTML parsing            │
│    • clean_signature() - Remove footers, quotes, separators    │
│    • Preserve core email content                               │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  LANGGRAPH WORKFLOW (Synchronous)               │
│                                                              │
│  ┌──────────┐  ┌───────────┐  ┌─────────┐  ┌───────────┐  │
│  │INGESTION │→ │EXTRACTION │→ │MATCHING*│→ │PERSISTENCE│  │
│  │   NODE   │  │   NODE    │  │  NODE   │  │   NODE     │  │
│  └──────────┘  └───────────┘  └─────────┘  └───────────┘  │
│                                    *conditional with --match   │
│                                           ↓                  │
│                                    ┌───────────┐       │
│                                    │ REPORTING │       │
│                                    │   NODE    │       │
│                                    └───────────┘       │
│                                                              │
│  Node Locations (src/analysis_workflow/nodes/):               │
│  • ingestion/ingestion.py - Load & parse .msg files          │
│  • extraction/extraction.py - LLM product extraction         │
│  • matching/matching.py - Hierarchical inventory matching    │
│    └─ utils/hierarchy.py - Property hierarchies           │
│    └─ utils/filtering.py - Database-driven filtering     │
│    └─ utils/matcher.py - Match scoring & ranking         │
│    └─ utils/normalizer.py - Property normalization       │
│  • persistence/persistence.py - Database storage with upsert │
│  • reporting/reporting.py - 5-sheet Excel generation         │
│                                                              │
│  State Machine (Pydantic BaseModel in src/models/workflow.py):│
│  {                                                            │
│    input_directory: str,                                      │
│    emails: List[Email] = [],                                  │
│    extracted_products: List[ProductMention] = [],             │
│    analytics: List[ProductAnalytics] = [],                    │
│    matching_enabled: bool = False,                            │
│    product_matches: List[InventoryMatch] = [],                │
│    review_flags: List[ReviewFlag] = [],                       │
│    report_path: str = "",                                       │
│    errors: List[str] = []  # Auto-initialized                 │
│  }                                                            │
└─────────────────────────────────────────────────────────────┘
│  │INGESTION │→ │EXTRACTION │→ │MATCHING │→ │PERSISTENCE  │→ │REPORTING ││
│  │   NODE   │  │   NODE    │  │  NODE*  │  │   NODE      │  │  NODE    ││
│  └──────────┘  └───────────┘  └─────────┘  └─────────────┘  └──────────┘│
│                                    *optional with --match flag             │
│                                                                 │
│  Ingestion:           Extraction:           Matching:           │
│  • Load .msg files    • Clean body text    • Load inventory    │
│  • Parse metadata     • LLM invoke()       • Fuzzy match props │
│  • Initial validation • Extract products   • Score confidence  │
│                       • Validate results    • Generate flags    │
│                                                                 │
│  Persistence:         Reporting:                                │
│  • Store emails       • Aggregate data                          │
│  • Store products     • Format tables                           │
│  • Store matches      • Add match/flag sheets                   │
│  • Store flags        • Generate Excel                          │
│                                                                 │
│  State Machine (Pydantic BaseModel):                            │
│  {                                                              │
│    input_directory: str,                                        │
│    emails: List[Email] = [],                                    │
│    extracted_products: List[ProductMention] = [],               │
│    analytics: List[ProductAnalytics] = [],                      │
│    inventory_items: List[InventoryItem] = [],                   │
│    product_matches: Dict[str, List[InventoryMatch]] = {},       │
│    review_flags: List[ReviewFlag] = [],                         │
│    report_path: str = "",                                       │
│    matching_enabled: bool = False,                              │
│    errors: List[str] = []  # Auto-initialized                   │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                 AI EXTRACTION LAYER                             │
│                  (Azure OpenAI GPT-5)                           │
│                                                                 │
│  Prompt Engineering:                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ System: You are analyzing industrial product emails.    │  │
│  │                                                          │  │
│  │ Extract:                                                 │  │
│  │ - Product names and categories                          │  │
│  │ - Properties (grade, size, material, finish, etc.)      │  │
│  │ - Quantities and units                                  │  │
│  │ - Context (quote request, order, inquiry)               │  │
│  │ - Dates mentioned                                       │  │
│  │                                                          │  │
│  │ Return: JSON array of products                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  LLM Configuration:                                             │
│  • Deployment: gpt-5                                            │
│  • API Version: 2024-08-01-preview                              │
│  • Temperature: 0 (deterministic extraction)                    │
│  • Reasoning effort: low                                        │
│  • Method: llm.invoke() - synchronous                           │
│  • Caching: Redis (localhost:6379)                              │
│  • Response: Structured JSON via with_structured_output()       │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                 INVENTORY MATCHING LAYER                        │
│          (Database-Driven Hierarchical Filtering)               │
│                                                                 │
│  Module: src/analysis_workflow/nodes/matching/utils/            │
│                                                                 │
│  Property Hierarchy (hierarchy.py):                             │
│  • Loads from config/products_config.yaml                       │
│  • Cached with @lru_cache for performance                      │
│  • Defines filter order: grade → size → length → material    │
│                                                                 │
│  Database Filtering (filtering.py):                             │
│  • Progressive SQL queries on inventory_items table            │
│  • Filters by category first (exact match)                     │
│  • Then by properties in hierarchy order                       │
│  • Uses JSON property column with GIN index                    │
│  • Stops when result set < 10 items (graceful degradation)    │
│  • 10-100x faster than in-memory linear scan                   │
│                                                                 │
│  Property Normalizer (normalizer.py):                           │
•  Normalize values: "Gr 8" → "8", "ss" → "stainless steel"    │
│  • Fuzzy match with rapidfuzz (80% similarity threshold)       │
│  • Batch normalization for performance                         │
│  • Handle common variations and typos                          │
│                                                                 │
│  Product Matcher (matcher.py):                                  │
│  • Calls database filtering to get candidates                  │
│  • Scores remaining items with weighted properties            │
│  • 40% name + 20% category + 40% properties                    │
│  • Ranks by score, returns top N matches                       │
│  • Generates match reasoning explanations                      │
│                                                                 │
│  Review Flag Generation:                                        │
│  • INSUFFICIENT_DATA - No matches found                        │
│  • LOW_CONFIDENCE - Score < 0.7                                │
│  • AMBIGUOUS_MATCH - Top 2 scores within 0.1                  │
│  • MISSING_PROPERTIES - ≥2 properties not in inventory         │
│  • Priority-coded actions for each flag type                   │
└────────────────────────────────────────────────────────────────┘
│  │ - Quantities and units                                  │  │
│  │ - Context (quote request, order, inquiry)               │  │
│  │ - Dates mentioned                                       │  │
│  │                                                          │  │
│  │ Return: JSON array of products                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  LLM Configuration:                                             │
│  • Deployment: gpt-4.1                                          │
│  • Temperature: 0 (deterministic extraction)                    │
│  • Method: llm.invoke() - synchronous                           │
│  • Response: Structured JSON                                    │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    OUTPUT GENERATION                            │
│                  (Excel Multi-Sheet Report)                     │
│                                                                 │
│  Sheet 1: PRODUCT MENTIONS (Detailed)                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Product | Category | Properties | Quantity | Context  │    │
│  │ Date | Email Subject | Sender | Source File            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Sheet 2: ANALYTICS (Aggregated)                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Product | Total Mentions | Date Range | Total Quantity │    │
│  │ Property Variations | Contexts | Unique Senders         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Sheet 3: EMAIL SUMMARY                                         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Email File | Subject | Sender | Date | Product Count  │    │
│  │ Has Attachments | Parse Status                          │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Sheet 4: INVENTORY MATCHES (if --match enabled)                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Product | Inventory Item # | Description | Match Score│    │
│  │ Rank | Matched Props | Missing Props | Reasoning      │    │
│  └────────────────────────────────────────────────────────┘    │
│  • Color-coded by score (green/yellow/orange)                  │
│  • NO MATCHES highlighted in red                                │
│                                                                 │
│  Sheet 5: REVIEW FLAGS (if --match enabled)                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Product | Issue Type | Match Count | Top Confidence   │    │
│  │ Reason | Action Needed                                  │    │
│  └────────────────────────────────────────────────────────┘    │
│  • Color-coded by priority (red/yellow/orange)                 │
│                                                                 │
│  Features:                                                      │
│  • Conditional formatting for easy reading                      │
│  • Frozen header rows                                           │
│  • Auto-filter columns                                          │
│  • Date formatting                                              │
│  • Pivot-table ready structure                                  │
└────────────────────────────────────────────────────────────────┘
```

## Data Models (Pydantic)

### Email Models

```python
EmailMetadata
  • message_id: Optional[str]
  • subject: str
  • sender: str
  • recipients: List[str]
  • cc: Optional[List[str]]
  • date: Optional[datetime]

Email
  • metadata: EmailMetadata
  • body: str
  • cleaned_body: Optional[str]
  • attachments: List[str]
  • file_path: Optional[str]
```

### Product Models

```python
ProductProperty
  • name: str (e.g., "grade", "size")
  • value: str
  • confidence: float (0.0 - 1.0)

ProductMention
  • exact_product_text: str  # Original text from email
  • product_name: str
  • product_category: str
  • properties: List[ProductProperty]
  • quantity: Optional[float]
  • unit: Optional[str]
  • context: str (quote_request, order, inquiry)
  • date_requested: Optional[str]
  • requestor: Optional[str]
  • email_subject: str
  • email_sender: str
  • email_file: Optional[str]

ProductAnalytics
  • product_name: str
  • product_category: str
  • total_mentions: int
  • first_mention: Optional[str]
  • last_mention: Optional[str]
  • total_quantity: Optional[float]
  • properties_summary: Dict[str, List[str]]
  • contexts: List[str]
  • people_involved: List[str]
```

### Inventory Models

```python
InventoryItem (extends ProductItem)
  • item_number: str  # Unique inventory ID
  • raw_description: str  # From Excel
  • exact_product_text: str
  • product_name: str
  • product_category: str
  • properties: List[ProductProperty]
  • parse_confidence: float
  • needs_manual_review: bool

InventoryMatch
  • inventory_item_number: str
  • inventory_description: str
  • match_score: float (0.0-1.0)
  • rank: int (1 = best match)
  • matched_properties: List[str]
  • missing_properties: List[str]
  • match_reasoning: str

ReviewFlag
  • product_text: str
  • product_name: str
  • product_category: str
  • issue_type: str  # INSUFFICIENT_DATA, LOW_CONFIDENCE, etc.
  • match_count: int
  • top_confidence: Optional[float]
  • reason: str
  • action_needed: str
```

## Technology Stack Justification

### Why These Libraries?

1. **PostgreSQL 17 + pgvector** (database)

   - ✅ Industry-standard relational database
   - ✅ pgvector extension for future semantic search
   - ✅ Strong ACID guarantees
   - ✅ Docker support for easy deployment
   - ✅ SQLAlchemy 2.0 compatibility

2. **SQLAlchemy 2.0** (ORM)

   - ✅ Modern async-capable ORM (using sync mode)
   - ✅ Type-safe queries with new syntax
   - ✅ Relationship management
   - ✅ Migration support via Alembic (future)
   - ✅ Connection pooling built-in

3. **rapidfuzz 3.14.3** (fuzzy matching)

   - ✅ Fast Levenshtein distance calculations
   - ✅ Multiple matching algorithms
   - ✅ Property normalization support
   - ✅ Active maintenance
   - ✅ Pure Python (no C deps)

4. **extract-msg** (vs mail-parser)

   - ✅ Already in requirements.txt
   - ✅ Specifically for Outlook .msg files
   - ✅ Handles RTF, HTML, plain text bodies
   - ✅ Extracts attachments and metadata
   - ❌ mail-parser: Not maintained since 2020, for standard email formats

5. **LangGraph** (vs raw LangChain)

   - ✅ State machine workflow management
   - ✅ Easy node composition
   - ✅ Built-in error handling
   - ✅ Synchronous execution support
   - ✅ Visual workflow representation
   - ✅ Redis caching integration

6. **BeautifulSoup4** (vs regex only)

   - ✅ Robust HTML parsing
   - ✅ Handles malformed HTML
   - ✅ Easy tag removal
   - ✅ Entity decoding
   - ✅ Preserves text content

7. **Pydantic v2** (vs dataclasses)

   - ✅ Runtime validation
   - ✅ JSON serialization
   - ✅ Type coercion
   - ✅ Documentation via models
   - ✅ OpenAPI integration ready

8. **openpyxl** (vs pandas/xlsxwriter)
   - ✅ Pure Python (no external deps)
   - ✅ Rich formatting support
   - ✅ Multiple sheet management
   - ✅ Formula support
   - ✅ Active maintenance

## Workflow Execution Flow

```
1. INITIALIZATION
   ├─ Load products_config.yaml
   ├─ Initialize Azure OpenAI client (with Redis caching)
   ├─ Test database connection (if --match flag)
   └─ Create LangGraph workflow

2. INGESTION PHASE
   ├─ Scan directory for .msg files
   ├─ Parse each email (extract-msg)
   ├─ Validate Email models
   └─ Add to workflow state

3. PREPROCESSING PHASE
   ├─ Strip HTML tags (BeautifulSoup)
   ├─ Remove signatures/footers
   ├─ Clean quoted text
   └─ Update Email.cleaned_body

4. EXTRACTION PHASE (per email)
   ├─ Build LLM prompt with:
   │  ├─ Product definitions from config
   │  ├─ Cleaned email body
   │  └─ Example extractions
   ├─ Call llm.invoke() - synchronous
   ├─ Parse JSON response via structured_output
   ├─ Validate ProductMention models
   └─ Add to state.extracted_products

5. MATCHING PHASE (if --match enabled)
   ├─ Load inventory items from database
   ├─ For each extracted product:
   │  ├─ Filter by category (exact match)
   │  ├─ Normalize properties (rapidfuzz)
   │  ├─ Calculate Jaccard similarity scores
   │  ├─ Rank matches by score
   │  └─ Generate review flags if needed
   └─ Update state with matches and flags

6. PERSISTENCE PHASE
   ├─ Store emails to emails_processed table
   ├─ Store products to product_mentions table (FK to emails)
   ├─ If matching enabled:
   │  ├─ Store matches to inventory_matches (FK to products & inventory)
   │  └─ Store flags to match_review_flags (FK to products)
   └─ Commit transactions

7. ANALYTICS PHASE
   ├─ Group products by name/category
   ├─ Calculate aggregates:
   │  ├─ Total mentions
   │  ├─ Date ranges
   │  ├─ Quantity sums
   │  └─ Property variations
   └─ Create ProductAnalytics models

8. REPORTING PHASE
   ├─ Create Excel workbook (openpyxl)
   ├─ Generate Sheet 1: Product Mentions
   ├─ Generate Sheet 2: Analytics
   ├─ Generate Sheet 3: Email Summary
   ├─ If matching enabled:
   │  ├─ Generate Sheet 4: Inventory Matches (color-coded)
   │  └─ Generate Sheet 5: Review Flags (priority-coded)
   ├─ Apply formatting and filters
   └─ Save to output directory

9. ERROR HANDLING
   ├─ Log parsing errors (continue processing)
   ├─ Record LLM failures
   ├─ Track validation failures
   ├─ Database transaction rollbacks
   └─ Generate error report in state
```

## Key Design Decisions Explained

### 1. No Email Threading

**Rationale**: Email thread reconstruction is complex and error-prone:

- Unreliable headers (In-Reply-To, References often missing)
- Subject line matching (RE:, FW: variations)
- Date/time alignment across timezones
- Out of scope for current requirements

**Solution**: Treat each email independently, extract all product mentions per email.

### 2. Synchronous Processing

**Rationale**:

- Simpler debugging and error tracking
- Easier to reason about execution flow
- No concurrency bugs
- Performance adequate for current scale (~10-20 emails/min)

**Trade-off**: Could process faster with async, but added complexity not worth it yet.

### 3. Test-Driven Development

**Rationale**:

- Catch bugs early in email parsing (complex format handling)
- Document expected behavior
- Enable confident refactoring
- Ensure LLM extraction reliability

**Current Coverage**: 26 passing tests across email parsing and signature cleaning.

### 4. Configurable Products

**Rationale**:

- Business requirements change frequently
- Different customers need different product types
- Properties vary by industry
- No code changes needed for new products

**Implementation**: YAML config with product definitions, aliases, and properties.

## Error Handling Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   ERROR CATEGORIES                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 1. PARSING ERRORS                                        │
│    • Corrupted .msg file → Skip file, log error         │
│    • Missing required fields → Use defaults             │
│    • Encoding issues → Fallback encoding                │
│                                                          │
│ 2. LLM ERRORS                                            │
│    • API timeout → Retry 3x with backoff                │
│    • Invalid JSON → Log, continue with empty result     │
│    • Rate limiting → Sleep and retry                    │
│                                                          │
│ 3. VALIDATION ERRORS                                     │
│    • Pydantic validation fail → Log details             │
│    • Missing required fields → Skip product             │
│    • Invalid dates → Use None                           │
│                                                          │
│ 4. REPORT GENERATION ERRORS                              │
│    • Excel write fail → Raise exception (fatal)         │
│    • Permission denied → Clear error message            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Performance Characteristics

**Current Benchmarks** (estimated):

- Email parsing: ~100ms per file
- Signature cleaning: ~50ms per email
- LLM extraction: ~2-5 seconds per email (Azure OpenAI latency)
- Excel generation: ~500ms for 100 rows

**Bottleneck**: Azure OpenAI API calls (synchronous)

**Scalability Path** (future):

1. Implement LLM response caching
2. Batch similar emails together
3. Switch to async if needed
4. Consider local LLM for faster processing

## Security Considerations

1. **API Keys**: Stored in `.env` file (gitignored)
2. **Email Content**: Processed locally, not sent to third parties (except Azure OpenAI)
3. **PII Handling**: Email addresses extracted but not filtered
4. **File Permissions**: Excel reports created with user permissions

## Maintenance & Monitoring

**Logging Strategy**:

- Info: Each phase completion
- Warning: Parsing failures (continue processing)
- Error: LLM failures, validation errors
- Debug: Detailed extraction results

**Metrics to Track**:

- Emails processed / failed
- Products extracted per email
- LLM call success rate
- Average processing time

## Future Enhancements (Not in Scope)

1. ❌ Email thread reconstruction (explicitly avoided)
2. ❌ Async processing (not needed yet)
3. ❌ Real-time processing (batch workflow)
4. ❌ Web interface (command-line only)
5. ✅ **Database storage** (PostgreSQL implemented)
6. ❌ Multi-language support (English only)
7. ❌ Semantic search with pgvector (prepared but not implemented)

## Deployment Requirements

**System Requirements**:

- Python 3.11+
- 4GB RAM minimum (for database + LLM caching)
- 500MB disk space
- Internet connection (Azure OpenAI)
- Docker & Docker Compose (for PostgreSQL)

**Infrastructure**:

- PostgreSQL 17 with pgvector extension
- Redis 7 for LLM response caching
- Docker containers for both services

**Dependencies**: See `requirements.txt` and `pyproject.toml`

Key libraries:

- extract-msg==0.55.0
- beautifulsoup4==4.13.5
- langgraph==1.0.3
- langchain-openai==1.0.2
- langchain-redis==0.1.6
- pydantic==2.12.4
- openpyxl==3.1.5
- sqlalchemy==2.0.36
- psycopg[binary]==3.2.12
- rapidfuzz==3.14.3
- pytest==9.0.1
- pyyaml==6.0.3

## Success Metrics

**Phase 1: Foundation** ✅ COMPLETE

- [x] 128/129 tests passing (99.2%)
- [x] Email parsing working
- [x] Signature cleaning implemented
- [x] Pydantic models defined

**Phase 2: Core Workflow** ✅ COMPLETE

- [x] LangGraph workflow implemented
- [x] Azure OpenAI integration working
- [x] Product extraction functional
- [x] Configuration system complete

**Phase 3: Database & Matching** ✅ COMPLETE

- [x] PostgreSQL database schema
- [x] SQLAlchemy models and operations
- [x] Inventory loader and parser
- [x] Fuzzy property matching
- [x] Product-to-inventory matching
- [x] Review flag generation

**Phase 4: Production Ready** ✅ COMPLETE

- [x] Excel report generation (5 sheets)
- [x] Integration tests passing (8/8)
- [x] End-to-end workflow complete
- [x] Documentation finalized
- [x] Database persistence working

**Phase 5: Deployment** 📋 IN PROGRESS

- [x] Docker Compose configuration
- [x] Database migration scripts
- [x] Import scripts for inventory
- [ ] Full inventory import (11,197 items)
- [ ] Production deployment guide

---

**Document Version**: 2.0  
**Last Updated**: November 14, 2025  
**Status**: Production Ready - Core Features Complete
