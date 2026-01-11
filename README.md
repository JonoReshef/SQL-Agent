# WestBrand Email Analysis System

## Overview

A **production-ready, full-stack** system for analyzing emails (`.msg` files) to extract product mentions, match them against inventory using **database-driven hierarchical filtering**, persist all data to **PostgreSQL**, and generate comprehensive **5-sheet Excel reports**. The system also includes a **natural language SQL chat interface** for querying the database. The system includes:

- **Email Analysis Backend**: Python-based analysis engine using **Azure OpenAI (gpt-5 with low reasoning effort)** orchestrated through **LangGraph** workflows with **fuzzy matching** for inventory reconciliation
- **SQL Chat Backend**: LangGraph-based natural language to SQL translation using **Azure OpenAI (gpt-4.1)** with conversation persistence and query transparency
- **REST API**: FastAPI server with Server-Sent Events (SSE) streaming for real-time chat responses
- **Frontend**: Modern Next.js 14 web interface with TypeScript and Tailwind CSS for interactive SQL chat
- **Infrastructure**: Docker Compose orchestration for PostgreSQL, Redis, backend, and frontend services

## Updated Architecture (November 2025)

### Key Design Decisions

1. **No Thread Reconstruction**: Each `.msg` file is analyzed as a single entity. No email threading or conversation reconstruction is performed.
2. **Synchronous Processing**: All email analysis operations are synchronous (no async/await) for simplicity. LLM calls use `.invoke()` not `.ainvoke()`. FastAPI server uses async for HTTP handling.
3. **Test-Driven Development**: Comprehensive unit and integration tests using `pytest`. Test suite includes 24 test files covering all major components.
4. **Database-First Architecture**: PostgreSQL 17 with content hashing and thread_hash as primary key for deduplication.
5. **Hierarchical Matching**: Database-driven property-based filtering (10-100x faster than linear scan) with fuzzy matching.
6. **Natural Language Database Interface**: SQL chat workflow enables querying the database with plain English questions.

### Technology Stack

| Component              | Technology             | License    | Purpose                                                          |
| ---------------------- | ---------------------- | ---------- | ---------------------------------------------------------------- |
| **Database**           | PostgreSQL 17          | PostgreSQL | Data persistence with pgvector                                   |
| **ORM**                | SQLAlchemy 2.0         | MIT        | Database operations and models                                   |
| **Email Parsing**      | extract-msg            | MIT        | Parse Outlook .msg files                                         |
| **HTML Processing**    | BeautifulSoup4         | MIT        | Strip HTML from email bodies                                     |
| **AI Orchestration**   | LangGraph              | MIT        | State machine workflow                                           |
| **LLM**                | AzureChatOpenAI        | MIT        | Product extraction (gpt-5) & SQL chat (gpt-4.1) via Azure OpenAI |
| **Fuzzy Matching**     | rapidfuzz              | MIT        | Hierarchical inventory matching                                  |
| **Data Models**        | Pydantic v2            | MIT        | Type-safe data structures                                        |
| **Configuration**      | PyYAML                 | MIT        | Product config management                                        |
| **Excel Output**       | openpyxl               | MIT        | Generate Excel reports                                           |
| **Caching**            | Redis                  | BSD        | LLM response caching                                             |
| **API Server**         | FastAPI                | MIT        | REST API with streaming support                                  |
| **Conversation State** | LangGraph Checkpointer | MIT        | Persistent conversation history                                  |
| **Frontend**           | Next.js 14             | MIT        | React-based web UI with TypeScript                               |
| **UI Components**      | Tailwind CSS           | MIT        | Responsive design system                                         |
| **Streaming UI**       | Server-Sent Events     | W3C        | Real-time response streaming                                     |
| **Testing**            | pytest                 | MIT        | Unit & integration tests                                         |

## Project Structure

```
WestBrand/
├── config/
│   └── products_config.yaml        # Product definitions & hierarchies
├── frontend/                        # Next.js web interface
│   ├── app/                        # Next.js app router
│   │   ├── chat/                   # Chat page
│   │   ├── layout.tsx              # Root layout
│   │   └── page.tsx                # Home page
│   ├── components/                 # React components
│   │   ├── ChatInterface.tsx       # Main chat container
│   │   ├── ChatSidebar.tsx         # Thread management
│   │   ├── ChatMessages.tsx        # Message display
│   │   ├── ChatInput.tsx           # Input field
│   │   └── helpers/                # Helper components
│   ├── hooks/                      # Custom React hooks
│   │   ├── useChatStream.ts        # SSE streaming logic
│   │   ├── useChatThreads.ts       # Thread management
│   │   └── useLocalStorage.ts      # Local storage wrapper
│   ├── lib/                        # Utilities
│   │   ├── api.ts                  # API client
│   │   └── utils.ts                # Helper functions
│   ├── types/                      # TypeScript types
│   │   ├── interfaces.ts           # Shared interfaces
│   │   └── server/                 # Auto-generated from API
│   ├── Dockerfile                  # Frontend container
│   ├── package.json                # npm dependencies
│   └── README.md                   # Frontend documentation
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
│   ├── server/
│   │   └── server.py               # FastAPI REST API (unified endpoint)
│   ├── chat_workflow/
│   │   ├── cli.py                  # CLI interface for testing
│   │   ├── graph.py                # LangGraph SQL chat workflow (4 nodes)
│   │   ├── prompts.py              # System prompts for SQL generation
│   │   ├── README.md               # Chat workflow documentation
│   │   ├── nodes/
│   │   │   ├── enrich_question.py      # Expand user questions
│   │   │   ├── generate_query.py       # Natural language to SQL
│   │   │   ├── execute_query.py        # SQL execution and tracking
│   │   │   └── generate_explanations.py # Query explanation generation
│   │   └── utils/
│   │       ├── db_wrapper.py       # PostgreSQL connection setup
│   │       └── tools.py            # LangChain tools (run_query, get_schema)
│   ├── inventory/
│   │   ├── loader.py               # Load inventory from Excel
│   │   └── parser.py               # Parse inventory with LLM
│   ├── llm/
│   │   ├── client.py               # Azure OpenAI client wrapper
│   │   └── extractors.py          # Product extraction logic
│   ├── config/
│   │   └── config_loader.py       # Load YAML configuration
│   ├── models/
│   │   ├── server.py              # FastAPI request/response models
│   │   └── ...                     # Other models
│   └── main.py                    # CLI entry point for email analysis
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
│   ├── test_integration.py        # End-to-end tests
│   └── chat_workflow/
│       ├── test_graph.py          # Chat workflow graph tests
│       ├── test_models.py         # Pydantic model tests
│       ├── test_nodes.py          # Individual node tests
│       └── test_db_wrapper.py     # Database wrapper tests
├── data/                          # Email .msg files
├── output/                        # Generated Excel reports
├── docker-compose.yml             # Full stack: PostgreSQL + Redis + Backend + Frontend
├── Dockerfile                     # Backend container
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

### 7. SQL Chat Workflow (`src/chat_workflow/`)

- ✅ 4-node LangGraph workflow: enrich_question → generate_query ↔ execute_query → generate_explanations
- ✅ Question enrichment to expand user queries for better intent understanding
- ✅ Natural language to SQL translation using Azure OpenAI gpt-4.1
- ✅ PostgreSQL checkpointer for conversation persistence (thread-based)
- ✅ Redis caching for LLM responses (reduces redundant API calls)
- ✅ Query transparency: all SQL displayed with AI-generated explanations
- ✅ Multi-query tracking with overall search process summary
- ✅ CLI interface for interactive testing
- ✅ Read-only query validation (SELECT only)
- ✅ Domain-specific system prompts for WestBrand database
- ✅ **anticipate_complexity** parameter for thorough vs. direct analysis

### 8. FastAPI REST API (`src/server/server.py`)

- ✅ Unified REST API endpoint combining email analysis and SQL chat
- ✅ Server-Sent Events (SSE) streaming for real-time responses
- ✅ Non-streaming fallback endpoint for compatibility
- ✅ CORS middleware for frontend integration
- ✅ Conversation history endpoint (`/history/{thread_id}`)
- ✅ Health check endpoint for monitoring
- ✅ Pydantic models for request/response validation
- ✅ Status updates during query processing
- ✅ Query transparency with AI-generated explanations

### 9. Next.js Frontend (`frontend/`)

- ✅ Modern React 18 with TypeScript and Next.js 14
- ✅ Real-time streaming chat interface using Server-Sent Events
- ✅ Multi-thread conversation management
- ✅ SQL query display with syntax highlighting
- ✅ Responsive mobile-first design with Tailwind CSS
- ✅ Local storage for conversation persistence
- ✅ Auto-generated TypeScript types from OpenAPI schema
- ✅ Copy-to-clipboard for SQL queries
- ✅ Delete thread confirmation dialogs
- ✅ Streaming status indicators

### 10. Docker Compose Deployment

- ✅ 4-service architecture: PostgreSQL, Redis, Backend, Frontend
- ✅ Health checks for all services
- ✅ Automatic dependency management
- ✅ Volume persistence for database and cache
- ✅ Network isolation with bridge networking
- ✅ Environment variable configuration
- ✅ Frontend served on port 3000
- ✅ Backend API on port 8000

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
    azure_deployment="gpt-4.1",  # Using gpt-4.1 deployment
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

### Full-Stack Deployment (Recommended)

The complete system (PostgreSQL + Redis + Backend + Frontend) can be deployed with Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop all services
docker-compose down
```

**Services:**

- **Frontend**: http://localhost:3000 (Next.js web interface)
- **Backend API**: http://localhost:8000 (FastAPI REST API)
- **PostgreSQL**: localhost:5432 (database)
- **Redis**: localhost:6379 (cache)

### Frontend Web Interface

Access the chat interface at http://localhost:3000:

**Features:**

- Real-time streaming responses
- Multiple conversation threads
- SQL query transparency with syntax highlighting
- Mobile-responsive design
- Local storage for conversation history
- Copy SQL queries to clipboard

**Configuration:**

- Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (default: http://localhost:8000)
- Backend must be running for frontend to function

See `frontend/README.md` for detailed frontend documentation.

### Prerequisites (Development)

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

### SQL Chat Interface

#### Web Interface (Recommended)

Access the chat interface at http://localhost:3000 after starting Docker Compose.

#### CLI Interface (Development/Testing)

Query the WestBrand database using natural language with automatic question enrichment and query transparency:

```bash
# Start the CLI interface
python -m src.chat_workflow.cli
```

#### REST API Endpoints

The backend API (`src/server/server.py`) provides:

**Example Chat Session:**

```
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
Retrieved the total count of emails by querying the emails_processed table.
======================================================================
```

**Key Features:**

- **Question Enrichment**: Automatically expands queries for better understanding
- **Query Transparency**: All SQL displayed with AI explanations
- **Conversation Persistence**: Thread-based history stored in PostgreSQL
- **Redis Caching**: LLM responses cached to reduce costs
- **Read-only Safety**: Only SELECT queries allowed
- **Anticipate Complexity**: Set `anticipate_complexity: true` for thorough analysis (default: false)

#### REST API Endpoints

The backend API (`src/server/server.py`) provides:

**Base URL**: http://localhost:8000

1. **POST /chat/stream** - Streaming chat with Server-Sent Events (SSE)
   - Real-time token streaming
   - Status updates during processing
   - Query transparency with explanations
   - Overall summary at completion

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many emails have been processed?",
    "thread_id": "user-123",
    "anticipate_complexity": false
  }'
```

2. **POST /chat** - Non-streaming chat (JSON response)
   - Complete response in single payload
   - All executed queries with explanations
   - Thread-based conversation continuity

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the top 5 most requested products",
    "thread_id": "user-123",
    "anticipate_complexity": false
  }'
```

3. **GET /history/{thread_id}** - Retrieve conversation history
   - All checkpoints and messages for a thread
   - Metadata and timestamps

```bash
curl http://localhost:8000/history/user-123
```

4. **GET /health** - Health check endpoint

```bash
curl http://localhost:8000/health
```

**Request Parameters:**

- `message` (string, required): User's question
- `thread_id` (string, required): Unique thread identifier for conversation continuity
- `anticipate_complexity` (boolean, optional, default: false):
  - `false`: Direct answers with minimal queries (faster)
  - `true`: Thorough exploratory analysis with more comprehensive queries

**Response Format (Streaming):**

Server-Sent Events with multiple event types:

```javascript
// Status update
data: {"type": "status", "content": "Executing query..."}

// Message chunk
data: {"type": "message", "content": "The database contains 156 emails."}

// Queries with transparency
data: {"type": "queries", "queries": [{"query": "SELECT COUNT(*) FROM emails_processed", "explanation": "Counts total emails", "result_summary": "Found 156 records"}]}

// Overall summary
data: {"type": "summary", "content": "Retrieved email count from database"}

// End of stream
data: {"type": "end"}

// Error (if any)
data: {"type": "error", "content": "Error message"}
```

**Response Format (Non-Streaming):**

```json
{
  "response": "The database contains 156 emails.",
  "thread_id": "user-123",
  "executed_queries": [
    {
      "query": "SELECT COUNT(*) FROM emails_processed",
      "explanation": "Counts the total number of processed email records",
      "result_summary": "Found 156 records"
    }
  ]
}
```

You: Show me the top 5 most requested products

🤖 Agent: The top 5 most requested products are:

1. Grade 8 Hex Bolts (42 mentions)
2. Threaded Rod (38 mentions)
3. Washers (31 mentions)
4. U-Bolts (27 mentions)
5. Anchor Bolts (23 mentions)

======================================================================
📊 SQL Queries Executed:
======================================================================

Query 1:
💡 Gets the top 5 products by mention count with their categories
📈 Result: Found 5 records

SQL:
SELECT product_name, product_category, COUNT(\*) as mentions
FROM product_mentions
GROUP BY product_name, product_category
ORDER BY mentions DESC
LIMIT 5;

======================================================================

```

See `src/chat_workflow/README.md` and `frontend/README.md` for complete documentation.

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
- ✅ LLM-based product extraction (Azure OpenAI gpt-5 with low reasoning effort)
- ✅ Database persistence (PostgreSQL with thread_hash + content_hash)
- ✅ Database-driven hierarchical matching (10-100x faster)
- ✅ Fuzzy property matching (rapidfuzz)
- ✅ Review flag generation (quality assurance)
- ✅ 5-sheet Excel reports (conditional formatting)
- ✅ LangGraph workflow orchestration
- ✅ Redis caching for LLM responses
- ✅ Docker Compose deployment
- ✅ Comprehensive test suite (24 test files covering all components)
- ✅ **SQL Chat Workflow** - Natural language database queries with question enrichment
- ✅ **FastAPI REST API** - Streaming and non-streaming endpoints with SSE
- ✅ **Token-by-token streaming** - LangGraph dual-stream mode with smooth display
- ✅ **Client-side buffering** - requestAnimationFrame loop for consistent 300 chars/sec rendering
- ✅ **Conversation Persistence** - Thread-based chat history in PostgreSQL
- ✅ **Query Transparency** - AI-generated SQL explanations and summaries
- ✅ **Next.js Frontend** - Modern web UI with TypeScript and Tailwind CSS
- ✅ **Server-Sent Events** - Real-time streaming responses with smooth typewriter effect
- ✅ **Docker Compose** - Full-stack deployment with 4 services
- ✅ **Anticipate Complexity** - Toggle between direct and thorough analysis modes

### Known Issues

- None currently - all core features operational

### Future Enhancements

- 🔄 Email linking in reports for source grounding
- 🔄 Web dashboard for reviewing matches interactively (in progress - frontend built)
- 🔄 Semantic search with pgvector
- 🔄 Automated scheduled email scanning
- 🔄 Query result caching in chat workflow
- 🔄 Multi-database support in chat interface
- 🔄 User authentication and authorization for frontend
- 🔄 Export chat history to PDF/markdown
- 🔄 Dark mode for frontend
- ❌ Email thread reconstruction (explicitly out of scope)
- ❌ Async processing (not needed at current scale)

---

**Status**: Production Ready (Full-Stack)
**Version**: 3.1
**Last Updated**: November 26, 2025

## Additional Documentation

- `STREAMING_ARCHITECTURE.md` - **Token-by-token streaming with client-side buffering architecture**
- `docs/` - **Documentation directory with quick references and visual guides**
  - `docs/README.md` - Documentation index and reading guide
  - `docs/STREAMING_QUICK_REFERENCE.md` - Quick reference for streaming
  - `docs/STREAMING_VISUAL_GUIDE.md` - Visual diagrams and timing charts
- `frontend/README.md` - Next.js frontend documentation and development guide
- `src/chat_workflow/README.md` - SQL Chat Workflow detailed documentation
- `src/server/server.py` - FastAPI REST API implementation with streaming
- `ENHANCED_SQL_TRANSPARENCY.md` - SQL transparency feature implementation
- `SQL_TRANSPARENCY_FEATURE.md` - Original transparency feature design
- `ARCHITECTURE.md` - Detailed system architecture
- `DATABASE_FILTERING_IMPLEMENTATION.md` - Hierarchical matching implementation
- `HIERARCHICAL_MATCHING_IMPLEMENTATION.md` - Matching system design
- `CONTENT_HASH_IMPLEMENTATION.md` - Database change detection
```
