# WestBrand Email Analysis - Architectural Overview

## Executive Summary

A **full-stack, production-ready system** for analyzing Outlook emails to extract product information, match against inventory using **database-driven hierarchical filtering**, and generate comprehensive 5-sheet Excel reports with full database persistence. The system also provides a **natural language SQL chat interface** for querying the database. The system includes:

- **Email Analysis Backend**: Python-based email analysis using Azure OpenAI (gpt-5 with low reasoning effort) orchestrated via LangGraph workflows with fuzzy matching
- **SQL Chat Backend**: LangGraph-based natural language to SQL translation using Azure OpenAI (gpt-4.1) with conversation persistence via PostgreSQL checkpointer
- **REST API**: FastAPI server with Server-Sent Events (SSE) streaming for real-time chat responses
- **Frontend**: Modern Next.js 14 web interface with TypeScript and Tailwind CSS for interactive SQL chat
- **Infrastructure**: Docker Compose deployment for PostgreSQL 17 (with pgvector), Redis, backend, and frontend services

The system processes individual `.msg` files (no threading), uses PostgreSQL 17 with **thread_hash** as primary key for deduplication, and provides a **natural language SQL chat interface** with conversation persistence.

**Key Features**:

- Synchronous email analysis with LLM extraction
- PostgreSQL database with thread_hash PKs and content_hash for all records
- Database-driven hierarchical matching (10-100x faster than linear scan)
- Fuzzy property matching using rapidfuzz
- Multi-sheet Excel reports (3 or 5 sheets based on --match flag)
- **Natural language SQL chat interface with conversation persistence**
- **FastAPI REST API with Server-Sent Events streaming**
- **Next.js 14 frontend with real-time chat UI**
- **Full-stack Docker Compose deployment**
- Production-ready with health checks and monitoring

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
│  • checkpoints (LangGraph conversation persistence)            │
│    - thread_id, checkpoint_id, parent_checkpoint_id            │
│    - checkpoint (JSONB), metadata (JSONB)                      │
│                                                                 │
│  Features:                                                      │
│  • Foreign key constraints with CASCADE deletes                 │
│  • Indexes on all FKs and content_hash columns                  │
│  • Upsert operations based on natural keys                      │
│  • Content hashing for intelligent change detection             │
│  • Conversation state persistence for chat workflow             │
│  • Docker Compose for easy deployment                           │
└────────────────────────────────────────────────────────────────┘
                        ↓                    ↓                  ↓
              EMAIL ANALYSIS           SQL CHAT            WEB FRONTEND
                 WORKFLOW             WORKFLOW              (Next.js 14)
        (src/analysis_workflow/)  (src/chat_workflow/)   (frontend/)
                   ↓                      ↓                     ↓
            ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
            │  LangGraph  │      │  LangGraph   │      │  React 18   │
            │  Email      │      │  SQL Chat    │      │  TypeScript │
            │  Processor  │      │  Agent       │      │  Tailwind   │
            └─────────────┘      └──────────────┘      └─────────────┘
                   ↓                      ↓                     ↓
            5-Sheet Excel         FastAPI Server         SSE Streaming
                Report           (src/server/server.py)   Chat Interface
                                           ↑                     ↓
                                           └─────────────────────┘
                                            REST API + SSE Events
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
│                  (Azure OpenAI gpt-4.1)                         │
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
│  • Deployment: gpt-4.1                                          │
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
│  LLM Configuration (Product Extraction):                        │
│  • Deployment: gpt-5                                            │
│  • Temperature: 0 (deterministic extraction)                    │
│  • Reasoning effort: low                                        │
│  • Method: llm.invoke() - synchronous                           │
│  • Response: Structured JSON via with_structured_output()       │
│                                                                 │
│  LLM Configuration (SQL Chat):                                  │
│  • Deployment: gpt-4.1                                          │
│  • Temperature: 0 (deterministic)                               │
│  • Method: llm.invoke() - synchronous                           │
│  • Response: Tool calls and messages                            │
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

### SQL Chat Models

```python
ChatState (LangGraph state)
  • messages: Annotated[List[BaseMessage], add]  # Conversation history
  • available_tables: List[str]  # Database table names
  • current_query: Optional[str]  # SQL being executed
  • query_result: Optional[str]  # Result from last query
  • error: Optional[str]  # Error messages
  • executed_queries: Annotated[List[QueryExecution], add]  # Query transparency
  • overall_summary: Optional[str]  # Search process summary

QueryExecution (for transparency)
  • query: str  # The actual SQL executed
  • query_explanation: QueryExplanation  # AI-generated explanation
  • raw_result: Optional[str]  # Query result

QueryExplanation
  • description: str  # One-line non-technical explanation
  • result_summary: str  # What was found (e.g., "Found 80 records")
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

## SQL Chat Workflow Architecture

### Overview

The **SQL Chat Workflow** (`src/chat_workflow/`) provides a natural language interface to query the WestBrand PostgreSQL database. Users can ask questions in plain English then the system enriches the queries using Azure OpenAI gpt-4.1 with prior conversational content then the system translates these to SQL queries using gpt-5. The system features **question enrichment** to better understand user intent, **query transparency** with AI-generated explanations, and **conversation persistence** for multi-turn interactions.

### Key Components

```
┌────────────────────────────────────────────────────────────────┐
│                   SQL CHAT WORKFLOW                             │
│                  (LangGraph State Machine)                      │
│                                                                 │
│  ┌──────────┐  ┌───────────┐  ┌─────────────┐  ┌──────────┐  │
│  │ Enrich   │→ │ Generate  │→ │  Execute    │→ │ Generate │  │
│  │ Question │  │  Query    │  │   Query     │  │ Explain. │  │
│  └──────────┘  └───────────┘  └─────────────┘  └──────────┘  │
│                       ↑               ↓                         │
│                       └───────────────┘                         │
│                    (Loop for follow-ups)                        │
│                                                                 │
│  State: ChatState (Pydantic v2 - src/models/chat_models.py)   │
│  • user_question: Current question being answered              │
│  • enriched_query: QuestionEnrichment (additional context)     │
│  • messages: Conversation history (add reducer)                │
│  • query_result: AIMessage with last LLM response              │
│  • executed_queries: List[QueryExecution] (transparency)       │
│  • overall_summary: AI-generated summary of search process     │
│  • available_tables: Discovered table names                    │
│  • current_query: Last SQL query executed                      │
│  • execute_result: Result from last query                      │
│  • error: Error message if operation failed                    │
│                                                                 │
│  Persistence: PostgreSQL Checkpointer (LangGraph)              │
│  • Thread-based conversation history                           │
│  • Survives server restarts                                    │
│  • Enables multi-turn conversations                            │
│  • Checkpoint tables: checkpoints, checkpoint_writes           │
│                                                                 │
│  Caching: Redis (LangChain cache)                              │
│  • Caches LLM responses to reduce redundant calls              │
│  • Shared across conversation threads                          │
└────────────────────────────────────────────────────────────────┘
```

### Node Responsibilities

1. **enrich_question** (`nodes/enrich_question.py`):

   - Takes user's original question
   - Uses LLM to expand into 1-3 detailed sub-questions
   - Provides context about user's intent and goals
   - Returns `QuestionEnrichment` with additional questions and intended goal

2. **generate_query** (`nodes/generate_query.py`):

   - Receives enriched question and conversation history
   - LLM with tool binding (`run_query_tool`, `get_schema_tool`)
   - Converts natural language to PostgreSQL queries
   - Can call tools multiple times to gather schema info
   - Returns AIMessage with tool_calls or final answer

3. **execute_query** (`nodes/execute_query.py`):

   - Extracts SQL from tool_calls in AIMessage
   - Validates queries are SELECT only (security)
   - Executes against PostgreSQL database
   - Creates `QueryExecution` objects with query and raw result
   - Appends to state.executed_queries for transparency
   - Returns ToolMessage with results

4. **generate_explanations** (`nodes/generate_explanations.py`):
   - Processes all queries in state.executed_queries
   - Generates AI explanations in parallel using ThreadPoolExecutor
   - Creates one-line non-technical descriptions
   - Generates result summaries ("Found 80 records")
   - Produces overall summary of entire search process
   - Updates QueryExecution objects with QueryExplanation

### Workflow Execution Flow

```
1. USER INPUT
   ├─ Natural language question (e.g., "How many emails were processed?")
   ├─ Thread ID for conversation continuity
   └─ Submit via CLI or REST API

2. ENRICH QUESTION NODE
   ├─ Receives user question and conversation history
   ├─ LLM generates 1-3 clarifying sub-questions
   ├─ Examples:
   │  User: "What were sales last quarter?"
   │  Enriched:
   │    1. Total sales figures for each month in last quarter
   │    2. Breakdown by product category
   │    3. Significant trends or anomalies
   ├─ Creates QuestionEnrichment object:
   │  {
   │    additional_questions: List[str],
   │    intended_goal: Optional[str]
   │  }
   └─ Adds HumanMessage to state with enriched context

3. GENERATE QUERY NODE
   ├─ Receives:
   │  ├─ Original user question
   │  ├─ Enriched questions and goals
   │  ├─ Conversation history (all previous messages)
   │  ├─ Previously executed queries and results
   │  └─ WestBrand system prompt with domain knowledge
   ├─ LLM bound with tools:
   │  ├─ run_query_tool: Execute PostgreSQL SELECT queries
   │  └─ get_schema_tool: Fetch table schemas dynamically
   ├─ LLM decides:
   │  ├─ Generate new SQL queries if more data needed
   │  ├─ Call get_schema_tool if schema info needed
   │  └─ Provide final answer if question fully answered
   ├─ Returns AIMessage with:
   │  ├─ tool_calls (if more queries needed) OR
   │  └─ content (final answer text)
   └─ Updates state.query_result

4. CONDITIONAL ROUTING (should_continue)
   ├─ Checks state.query_result.tool_calls
   ├─ If tool_calls exist → go to EXECUTE QUERY
   └─ If no tool_calls → go to GENERATE EXPLANATIONS (done)

5. EXECUTE QUERY NODE (if tool calls present)
   ├─ Iterates through all tool_calls
   ├─ For each run_query_tool call:
   │  ├─ Extract SQL query from tool arguments
   │  ├─ Validate: Must be SELECT only (security)
   │  ├─ Execute query against PostgreSQL
   │  ├─ Create QueryExecution object:
   │  │  {
   │  │    query: str (the SQL),
   │  │    raw_result: str (database result),
   │  │    query_explanation: None (filled later)
   │  │  }
   │  └─ Append to state.executed_queries
   ├─ Creates ToolMessage for each result
   ├─ Updates state.current_query and execute_result
   └─ Loops back to GENERATE QUERY for next step

6. GENERATE EXPLANATIONS NODE (when done querying)
   ├─ Receives all QueryExecution objects from state
   ├─ For each query (parallel with ThreadPoolExecutor):
   │  ├─ Sends query + result to LLM
   │  ├─ LLM generates QueryExplanation:
   │  │  {
   │  │    description: "One-line non-technical explanation",
   │  │    result_summary: "Found 80 records" or similar
   │  │  }
   │  └─ Adds explanation to QueryExecution
   ├─ Generates overall_summary:
   │  └─ AI summary of entire multi-query search process
   ├─ Updates state with explained queries
   └─ Workflow ends (returns to user)

7. PERSISTENCE (automatic at each step)
   ├─ LangGraph PostgresSaver checkpoints every state change
   ├─ Checkpoint includes:
   │  ├─ thread_id (conversation identifier)
   │  ├─ checkpoint_id (unique per state)
   │  ├─ Full message history
   │  ├─ All executed queries with explanations
   │  └─ Metadata (step number, timestamp)
   └─ Enables conversation resume and history retrieval

8. FINAL RESPONSE TO USER
   ├─ Natural language answer from LLM
   ├─ All executed queries with:
   │  ├─ 💡 One-line explanation
   │  ├─ 📈 Result summary
   │  └─ Formatted SQL query
   └─ Overall summary of search process
```

### Data Models

#### State Models (`src/models/chat_models.py`)

```python
class QuestionEnrichment(BaseModel):
    """Enrichment details for user question"""
    additional_questions: List[str]  # Clarifying sub-questions
    intended_goal: Optional[str]     # Why these questions help

class QueryExplanation(BaseModel):
    """AI-generated explanation of query execution"""
    description: str                 # One-line non-technical explanation
    result_summary: str | None       # "Found 80 records" or similar

class QueryExecution(BaseModel):
    """Single SQL query execution with transparency"""
    query: str                       # The actual SQL
    raw_result: Optional[str]        # Database result
    query_explanation: Optional[QueryExplanation]  # AI explanation

class ChatState(BaseModel):
    """LangGraph state for SQL chat workflow"""
    user_question: str                              # Current question
    enriched_query: QuestionEnrichment              # Expanded context
    messages: Annotated[List[BaseMessage], add]     # Conversation history (add reducer)
    query_result: AIMessage                         # Last LLM response
    executed_queries: List[QueryExecution]          # All queries (transparency)
    overall_summary: Optional[str]                  # AI summary of search
    available_tables: List[str]                     # Discovered tables
    current_query: Optional[str]                    # Last SQL executed
    execute_result: Optional[str]                   # Last query result
    error: Optional[str]                            # Error if any
```

**Key Features:**

- Pydantic v2 with `ConfigDict(arbitrary_types_allowed=True)` for LangChain types
- `messages` uses `add` reducer (never overwrites, always appends)
- All queries tracked in `executed_queries` for full transparency
- AI-generated explanations added post-execution

### API Interfaces

#### 1. CLI Interface (`cli.py`)

```bash
python -m src.chat_workflow.cli

# Interactive REPL with question enrichment and query transparency
You: How many emails are in the system?

Enriching question...
🤖 Agent: There are 156 emails in the database.

======================================================================
📊 SQL Queries Executed:
======================================================================

Query 1:
  💡 Counts the total number of processed email records
  📈 Result: Found 156 records

  SQL:
    SELECT COUNT(*) AS email_count FROM emails_processed;

Overall Summary:
Retrieved total email count by querying emails_processed table.
======================================================================
```

#### 2. REST API (`api.py` - FastAPI)

**Status**: API implementation exists but may require updates to match current workflow (4-node design with enrichment and explanations).

**Non-Streaming Endpoint:**

```bash
POST /chat
{
  "message": "How many emails are in the system?",
  "thread_id": "user-123"
}

Response:
{
  "response": "There are 156 emails in the database.",
  "executed_queries": [
    {
      "query": "SELECT COUNT(*) FROM emails_processed;",
      "query_explanation": {
        "description": "Counts total processed emails",
        "result_summary": "Found 156 records"
      },
      "raw_result": "[(156,)]"
    }
  ],
  "overall_summary": "Retrieved email count from database."
}
```

**Streaming Endpoint:**

```bash
POST /chat/stream
Server-Sent Events (SSE):
data: {"type": "token", "content": "There"}
data: {"type": "token", "content": " are"}
data: {"type": "sql", "query": "SELECT COUNT(*)..."}
data: {"type": "end"}
```

data: {"type": "end"}

````

### Key Features

#### Query Transparency

**Every query execution is tracked with AI-generated explanations for full transparency.**

**Benefits**:
- Users understand what SQL is being run
- Educational - learn SQL by example
- Debugging - verify query correctness
- Audit trail - track database access
- Multi-query workflow visibility

**Implementation** (`QueryExecution` model):

```python
QueryExecution
  • query: str  # Actual SQL executed
  • query_explanation: QueryExplanation
    - description: str  # "Counts total emails in database"
    - result_summary: str  # "Found 156 records"
  • raw_result: Optional[str]  # Database result: "[(156,)]"
````

**Display Format**:

```
Query 1:
  💡 Counts the total number of processed email records
  📈 Result: Found 156 records

  SQL:
    SELECT COUNT(*) FROM emails_processed;
```

#### Question Enrichment

**LLM expands user questions into detailed sub-questions** to better understand intent.

**Example**:

```
User: "What were sales last quarter?"

Enriched Questions:
1. Total sales figures for each month in last quarter
2. Breakdown by product category
3. Significant trends or anomalies

Intended Goal: Provide comprehensive quarterly sales analysis
```

**Implementation** (`QuestionEnrichment` model):

```python
QuestionEnrichment
  • additional_questions: List[str]  # 1-3 clarifying questions
  • intended_goal: Optional[str]     # Why these help
```

#### Conversation Persistence

**PostgreSQL checkpointer** stores full conversation history:

- Thread ID links related conversations
- Survives server restarts
- Enables conversation resume
- Full message history with state

**Tables** (auto-created by LangGraph):

- `checkpoints`: Main checkpoint storage
- `checkpoint_writes`: Intermediate writes

#### Safety Features

**Read-Only SQL Enforcement**:

- Only SELECT queries allowed
- INSERT, UPDATE, DELETE rejected
- DDL operations (DROP, ALTER, CREATE) blocked
- Query validation before execution

### Security Features

1. **Read-Only Access**: Only SELECT queries allowed (validated with regex)
2. **SQL Injection Protection**: Uses psycopg parameterized queries
3. **Error Handling**: Database errors caught and returned as error messages
4. **No DDL/DML**: CREATE, DROP, INSERT, UPDATE, DELETE all blocked

### Conversation Persistence

**PostgreSQL Checkpointer** (`langgraph-checkpoint-postgres`):

- Stores conversation state in `checkpoints` table
- Each message adds a new checkpoint
- Thread ID links related checkpoints
- Enables conversation history retrieval
- Survives server restarts

**Checkpoint Schema**:

```sql
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_id TEXT PRIMARY KEY,
    parent_checkpoint_id TEXT,
    checkpoint JSONB,  -- Full state snapshot
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Testing

**Test Coverage** (52/56 tests passing - 93%):

- `test_graph.py`: Workflow state machine tests (3 tests need updates)
- `test_api.py`: FastAPI endpoint tests
- `test_execute_query.py`: SQL execution tests
- `test_list_tables.py`: Table discovery tests
- `test_models.py`: Pydantic model validation tests
- `test_sql_transparency.py`: Query transparency tests (1 test needs update)
- `test_db_wrapper.py`: Database wrapper tests

### Domain Knowledge (System Prompts)

**Custom prompts** (`prompts.py`) include:

- WestBrand database schema context
- Common query patterns (email counts, product mentions, etc.)
- Property extraction logic
- Inventory matching concepts
- Best practices for SQL generation

**Example prompt snippet**:

```
You are a SQL expert helping users query the WestBrand database.

Available tables:
- emails_processed: Email metadata (subject, sender, date)
- product_mentions: Extracted products from emails
- inventory_items: Available inventory with properties
- inventory_matches: Product-to-inventory matches
- match_review_flags: Quality issues with matches

Always use SELECT queries only. Never modify data.
Provide clear explanations for every query.
```

## FastAPI REST API Architecture (`src/server/server.py`)

### Overview

The **unified REST API** provides HTTP endpoints for both email analysis and SQL chat functionality, with **Server-Sent Events (SSE)** streaming support for real-time responses. This single server handles all backend API requests from the frontend and other clients.

### Key Features

1. **Unified Endpoint**: Single server for all API functionality
2. **Server-Sent Events Streaming**: Real-time response streaming
3. **Non-Streaming Fallback**: JSON responses for compatibility
4. **CORS Middleware**: Frontend integration support
5. **Conversation Persistence**: Thread-based history via PostgreSQL
6. **Query Transparency**: All SQL queries with explanations
7. **Health Monitoring**: Health check endpoint
8. **Anticipate Complexity**: Toggle analysis depth

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     FASTAPI SERVER                              │
│                  (src/server/server.py)                         │
│                                                                 │
│  Middleware:                                                    │
│  • CORSMiddleware (allow_origins=["*"] - dev mode)            │
│                                                                 │
│  Endpoints:                                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ GET /                                                     │ │
│  │   Root with API information                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ POST /chat/stream (PRIMARY)                              │ │
│  │   • Server-Sent Events streaming                         │ │
│  │   • Real-time status updates                             │ │
│  │   • Token-by-token response streaming                    │ │
│  │   • Query transparency with explanations                 │ │
│  │   • Overall summary at completion                        │ │
│  │                                                           │ │
│  │ Request: ChatRequest (Pydantic)                          │ │
│  │   • message: str (user question)                         │ │
│  │   • thread_id: str (conversation continuity)             │ │
│  │   • anticipate_complexity: bool (analysis depth)         │ │
│  │                                                           │ │
│  │ Response: StreamingResponse (text/event-stream)          │ │
│  │   Event types:                                           │ │
│  │   • status: Processing updates                           │ │
│  │   • message: AI response content                         │ │
│  │   • queries: SQL with explanations/summaries             │ │
│  │   • summary: Overall workflow summary                    │ │
│  │   • end: Stream completion                               │ │
│  │   • error: Error messages                                │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ POST /chat (FALLBACK)                                    │ │
│  │   • Non-streaming JSON response                          │ │
│  │   • Complete response in single payload                  │ │
│  │   • Same request model as streaming                      │ │
│  │                                                           │ │
│  │ Response: ChatResponse (Pydantic)                        │ │
│  │   • response: str (full answer)                          │ │
│  │   • thread_id: str (echo back)                           │ │
│  │   • executed_queries: List[QueryExecutionResponse]       │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ GET /history/{thread_id}                                 │ │
│  │   • Retrieves conversation history                       │ │
│  │   • All checkpoints with messages                        │ │
│  │   • Metadata and timestamps                              │ │
│  │                                                           │ │
│  │ Response: HistoryResponse (Pydantic)                     │ │
│  │   • thread_id: str                                       │ │
│  │   • history: List[CheckpointData]                        │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ GET /health                                              │ │
│  │   • Health check for monitoring                          │ │
│  │   • Returns {"status": "healthy"}                        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Graph Integration:                                             │
│  • Singleton pattern for graph instance                        │
│  • get_graph() function caches LangGraph workflow              │
│  • Synchronous execution in async wrapper                      │
│  • PostgreSQL checkpointer for state persistence               │
└────────────────────────────────────────────────────────────────┘
```

### Request/Response Models (`src/models/server.py`)

```python
class ChatRequest(BaseModel):
    message: str  # User's question
    thread_id: str  # Conversation thread ID
    anticipate_complexity: bool = False  # Analysis depth toggle

class QueryExecutionResponse(BaseModel):
    query: str  # Executed SQL
    explanation: str  # Human-readable description
    result_summary: str  # Brief result summary

class ChatResponse(BaseModel):
    response: str  # Agent's answer
    thread_id: str  # Thread ID
    executed_queries: list[QueryExecutionResponse]  # Query transparency

class MessageHistory(BaseModel):
    type: str  # Message type (HumanMessage, AIMessage)
    content: str  # Message content

class CheckpointData(BaseModel):
    checkpoint_id: str
    messages: list[MessageHistory]
    timestamp: Optional[str]
    metadata: dict[str, Any]

class HistoryResponse(BaseModel):
    thread_id: str
    history: list[CheckpointData]
```

### Anticipate Complexity Feature

Controls analysis depth and thoroughness:

- **`false` (default)**: Direct answers with minimal queries

  - Skips question enrichment
  - Max 10 query iterations
  - Faster execution
  - Best for straightforward questions

- **`true`**: Thorough exploratory analysis
  - Performs question enrichment (1-3 sub-questions)
  - Max 30 query iterations
  - Comprehensive results
  - Best for complex, ambiguous questions

### Server-Sent Events (SSE) Implementation

**Streaming Workflow**:

1. Client opens SSE connection to `/chat/stream`
2. Server streams events as workflow progresses:
   - Status updates during processing
   - Final AI message when complete
   - All executed queries with explanations
   - Overall summary of workflow
   - End event to close connection
3. Client processes events in real-time
4. Connection closes after end event

**Event Format** (JSON in `data:` field):

```javascript
data: {"type": "status", "content": "Executing query..."}
data: {"type": "message", "content": "The database contains 156 emails."}
data: {"type": "queries", "queries": [...]}
data: {"type": "summary", "content": "Retrieved email count"}
data: {"type": "end"}
```

### Running the Server

```bash
# Development with auto-reload
uvicorn src.server.server:app --reload --host 0.0.0.0 --port 8000

# Production via Docker Compose
docker-compose up -d backend

# Direct execution
python -m src.server.server
```

### CORS Configuration

**Current**: `allow_origins=["*"]` (development mode)

**Production**: Must restrict to specific frontend domains:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Next.js Frontend Architecture (`frontend/`)

### Overview

The **frontend** is a modern web application built with **Next.js 14**, **React 18**, and **TypeScript**, providing a real-time streaming chat interface for the WestBrand SQL Chat Agent. It uses **Server-Sent Events** for live response streaming and **Tailwind CSS** for responsive design.

### Key Features

1. **Real-time Streaming**: Token-by-token response display via SSE
2. **Multi-Thread Management**: Create, switch, delete conversation threads
3. **SQL Transparency**: Syntax-highlighted queries with copy-to-clipboard
4. **Responsive Design**: Mobile-first with collapsible sidebar
5. **Local Storage Persistence**: Conversations saved in browser
6. **Type Safety**: Auto-generated types from backend OpenAPI schema
7. **Error Handling**: Graceful connection management

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     NEXT.JS 14 FRONTEND                         │
│                      (React 18 + TypeScript)                    │
│                                                                 │
│  App Router (app/):                                             │
│  ├── layout.tsx          Root layout with metadata             │
│  ├── page.tsx            Home (redirects to /chat)             │
│  ├── globals.css         Tailwind CSS + global styles          │
│  └── chat/                                                      │
│      └── page.tsx        Main chat page                        │
│                                                                 │
│  Component Hierarchy:                                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ChatInterface (Container)                                │ │
│  │ ├── ChatSidebar                                          │ │
│  │ │   ├── New Thread Button                                │ │
│  │ │   └── ThreadItem[]                                     │ │
│  │ │       └── Delete Button (with confirmation)            │ │
│  │ ├── ChatMessages                                         │ │
│  │ │   ├── Message[] (User/Assistant)                       │ │
│  │ │   │   ├── Markdown rendering                           │ │
│  │ │   │   └── QueryDisplay (SQL transparency)              │ │
│  │ │   │       ├── Syntax highlighted SQL                   │ │
│  │ │   │       ├── Explanation text                         │ │
│  │ │   │       ├── Result summary                           │ │
│  │ │   │       └── Copy to clipboard button                 │ │
│  │ │   └── StreamingIndicator (loading state)               │ │
│  │ └── ChatInput                                            │ │
│  │     ├── Auto-resizing textarea                           │ │
│  │     └── Send button                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Custom Hooks (hooks/):                                         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ useChatStream                                            │ │
│  │   • Manages SSE connection to backend                    │ │
│  │   • Handles event types (status, message, queries, etc.)│ │
│  │   • Automatic reconnection on errors                     │ │
│  │   • Cleanup on unmount                                   │ │
│  │   • Loading state management                             │ │
│  │                                                           │ │
│  │ Returns:                                                 │ │
│  │   • messages: Message[]                                  │ │
│  │   • isStreaming: boolean                                 │ │
│  │   • error: string | null                                 │ │
│  │   • sendMessage(text: string): void                      │ │
│  │   • stopStreaming(): void                                │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ useChatThreads                                           │ │
│  │   • Thread state management                              │ │
│  │   • localStorage persistence                             │ │
│  │   • Auto-save on changes                                 │ │
│  │                                                           │ │
│  │ Returns:                                                 │ │
│  │   • threads: Thread[]                                    │ │
│  │   • activeThreadId: string                               │ │
│  │   • createThread(): void                                 │ │
│  │   • switchThread(id: string): void                       │ │
│  │   • deleteThread(id: string): void                       │ │
│  │   • updateThreadName(id, name): void                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ useLocalStorage                                          │ │
│  │   • Generic localStorage wrapper                         │ │
│  │   • TypeScript support                                   │ │
│  │   • Auto-serialization                                   │ │
│  │                                                           │ │
│  │ const [value, setValue] = useLocalStorage<T>(key, init) │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Type Generation (scripts/):                                    │
│  • generate-types.cjs - OpenAPI to TypeScript                  │
│  • npm run sync-types - Auto-generate from backend             │
│  • Output: types/server/server-types.ts                        │
│                                                                 │
│  Libraries:                                                     │
│  • next: ^14.0.4                                                │
│  • react: ^18.2.0                                               │
│  • react-markdown: ^10.1.0 (markdown rendering)                │
│  • react-syntax-highlighter: ^15.5.0 (SQL highlighting)        │
│  • tailwindcss: ^3.4.0 (styling)                                │
│  • openapi-typescript: ^6.7.3 (type generation)                │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. USER INTERACTION
   User types message → Send button click
   ↓
2. FRONTEND STATE UPDATE
   useChatStream.sendMessage() called
   ↓
3. SSE CONNECTION OPENED
   EventSource connects to /chat/stream
   Request: {message, thread_id, anticipate_complexity}
   ↓
4. BACKEND PROCESSING
   LangGraph workflow executes
   ↓
5. REAL-TIME STREAMING
   Events streamed back:
   • status: "Executing query..."
   • message: "The database contains..."
   • queries: [{"query": "SELECT...", "explanation": "..."}]
   • summary: "Retrieved email count..."
   • end: (close stream)
   ↓
6. FRONTEND RENDERING
   • Streaming indicator shows during processing
   • Messages appear in chat as received
   • SQL queries rendered with syntax highlighting
   • Copy buttons enabled for SQL queries
   • Conversation saved to localStorage
```

### Environment Configuration

`frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Running the Frontend

```bash
# Development mode
cd frontend
npm install
npm run dev  # http://localhost:3000

# Production build
npm run build
npm start

# Docker (via docker-compose)
docker-compose up -d frontend
```

### Deployment (Docker)

**Multi-stage Dockerfile**:

1. **Build stage**: npm install + next build
2. **Production stage**: node + next start
3. **Exposed port**: 3000

**Included in `docker-compose.yml`** as `westbrand-frontend` service:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: westbrand-frontend
  environment:
    NEXT_PUBLIC_API_URL: http://localhost:8000
  ports:
    - '3000:3000'
  depends_on:
    - backend
  networks:
    - westbrand-network
  restart: unless-stopped
```

### Type Safety

**Auto-generated types from backend OpenAPI schema**:

```bash
# Generate types
npm run sync-types

# Uses openapi-typescript package
# Reads from: http://localhost:8000/openapi.json
# Writes to: types/server/server-types.ts
```

**Ensures frontend/backend type consistency**.

### Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile: iOS Safari, Chrome Mobile

### Performance Optimizations

1. **Code Splitting**: Next.js automatic route-based splitting
2. **Lazy Loading**: Components loaded on demand
3. **Local Storage**: Reduce backend calls for thread management
4. **SSE Streaming**: Incremental rendering for better perceived performance
5. **React 18 Concurrent Features**: Automatic batching and transitions

## Docker Compose Deployment Architecture

### Overview

The complete system is deployed using **Docker Compose** with 4 services: PostgreSQL, Redis, Backend, and Frontend. This provides a production-ready environment with health checks, volume persistence, and proper networking.

### Services

```yaml
services:
  pgdb: # PostgreSQL 17 with pgvector
    image: pgvector/pgvector:pg17
    container_name: westbrand-db
    ports: ['5432:5432']
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: pg_isready checks
    restart: unless-stopped

  redis: # Redis Stack Server
    image: redis/redis-stack-server:latest
    container_name: westbrand-redis
    ports: ['6379:6379']
    volumes: [redis_data:/data]
    healthcheck: redis-cli ping
    restart: unless-stopped

  backend: # Python FastAPI Server
    build: .
    container_name: westbrand-backend
    ports: ['8000:8000']
    environment:
      - AZURE_LLM_API_KEY
      - AZURE_LLM_ENDPOINT
      - DATABASE_URL=postgresql://${PGUSER}:${PGPASSWORD}@pgdb:5432/${PGDATABASE}
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis: { condition: service_healthy }
      pgdb: { condition: service_healthy }
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./config:/app/config
    restart: unless-stopped

  frontend: # Next.js 14 Web UI
    build: ./frontend
    container_name: westbrand-frontend
    ports: ['3000:3000']
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]
    restart: unless-stopped

volumes:
  redis_data:
  pgdata:

networks:
  westbrand-network:
    driver: bridge
```

### Deployment Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Service URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Health Checks

All services include health checks for reliable startup:

- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command
- **Backend**: Depends on healthy database and cache
- **Frontend**: Depends on healthy backend

### Volume Persistence

- **`pgdata`**: PostgreSQL database files (persistent)
- **`redis_data`**: Redis cache files (persistent)
- **`./data`**: Email .msg files (bind mount)
- **`./output`**: Generated Excel reports (bind mount)
- **`./config`**: Configuration files (bind mount)

### Network Isolation

All services communicate via **`westbrand-network`** bridge network:

- Inter-service communication uses service names (e.g., `pgdb`, `redis`)
- Isolated from other Docker networks
- Exposed ports for external access

## Future Enhancements (Not in Scope)

1. ❌ Email thread reconstruction (explicitly avoided)
2. ❌ Async processing (not needed yet)
3. ❌ Real-time processing (batch workflow)
4. ✅ **Natural language database interface** (SQL Chat implemented)
5. ✅ **Database storage** (PostgreSQL implemented)
6. ❌ Multi-language support (English only)
7. ❌ Semantic search with pgvector (prepared but not implemented)
8. ✅ **Chat workflow web UI** (Next.js frontend implemented)
9. ✅ **FastAPI REST API with streaming** (Server-Sent Events implemented)
10. ✅ **Full-stack Docker Compose deployment** (4-service architecture implemented)
11. 🔄 Query result caching
12. 🔄 Multi-database support
13. 🔄 User authentication and authorization
14. 🔄 Dark mode for frontend
15. 🔄 Export chat history to PDF/markdown

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
- langgraph-checkpoint-postgres==2.0.13
- langchain-openai==1.0.2
- langchain-redis==0.1.6
- pydantic==2.12.4
- openpyxl==3.1.5
- sqlalchemy==2.0.36
- psycopg[binary]==3.2.12
- rapidfuzz==3.14.3
- fastapi==0.115.5
- uvicorn[standard]==0.34.0
- pytest==9.0.1
- pyyaml==6.0.3

## Success Metrics

**Phase 1: Foundation** ✅ COMPLETE

- [x] Comprehensive test coverage (24 test files)
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

**Phase 5: Deployment** ✅ COMPLETE

- [x] Docker Compose configuration
- [x] Database migration scripts
- [x] Import scripts for inventory
- [x] SQL Chat Workflow with FastAPI
- [x] Natural language database queries
- [x] Conversation persistence via PostgreSQL checkpointer
- [x] Query transparency with AI explanations
- [x] Comprehensive test suite operational
- [ ] Full inventory import (11,197 items)
- [ ] Production deployment guide

---

**Document Version**: 3.1  
**Last Updated**: November 26, 2025  
**Status**: Production Ready - Full-Stack System Operational
