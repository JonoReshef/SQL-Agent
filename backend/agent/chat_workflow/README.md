# WestBrand SQL Chat Agent

A natural language interface to the WestBrand database using LangGraph and FastAPI.

## Overview

The SQL Chat Agent allows users to query the WestBrand PostgreSQL database using natural language. It uses Azure OpenAI gpt-4.1 to convert questions into SQL queries, execute them safely (read-only), and return formatted results with comprehensive transparency features including query explanations and overall summaries.

## Architecture

### Technology Stack

- **LangGraph**: State management and workflow orchestration
- **FastAPI**: REST API with streaming support (Server-Sent Events)
- **Azure OpenAI gpt-4.1**: Natural language to SQL conversion
- **PostgreSQL**: Database backend with conversation persistence (checkpointer)
- **Pydantic v2**: Type-safe state models
- **Redis**: LLM response caching

### Workflow Nodes

The SQL Chat Agent uses a 4-node LangGraph workflow:

1. **Enrich Question** (`nodes/enrich_question.py`): Expands user questions into 1-3 detailed sub-questions for better context and intent understanding
2. **Generate Query** (`nodes/generate_query.py`): Uses LLM with tool binding to convert natural language to SQL queries, with access to `run_query_tool` and `get_schema_tool`
3. **Execute Query** (`nodes/execute_query.py`): Validates and executes SQL queries (SELECT only), tracks executed queries for transparency
4. **Generate Explanations** (`nodes/generate_explanations.py`): Creates AI-generated explanations and summaries for all executed queries

**Workflow Loop**: After executing queries, the workflow loops back to `generate_query` to allow follow-up questions or generate the final answer when complete.

### Key Features

- ✅ **Read-only access**: Only SELECT queries allowed
- ✅ **Conversation persistence**: PostgreSQL-based checkpointing with thread IDs
- ✅ **Streaming responses**: Server-Sent Events (SSE)
- ✅ **Multi-turn conversations**: Maintains context across queries
- ✅ **Question enrichment**: Automatically expands ambiguous questions
- ✅ **Query transparency**: All SQL queries displayed with AI-generated explanations
- ✅ **Domain knowledge**: WestBrand-specific system prompts
- ✅ **Type-safe**: Pydantic v2 models with full validation
- ✅ **Redis caching**: Reduces redundant LLM calls

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL 17 database running (Docker Compose recommended)
- Redis running (Docker Compose recommended)
- Azure OpenAI API access (gpt-4.1 deployment)

### Install Dependencies

```bash
# Install required packages
pip install langgraph-checkpoint-postgres fastapi uvicorn[standard]

# Or add to requirements.txt:
# langgraph-checkpoint-postgres
# fastapi
# uvicorn[standard]
```

### Environment Variables

Add to `.env`:

```bash
DATABASE_URL=postgresql://westbrand:<password>@localhost:5432/westbrand_db
AZURE_LLM_API_KEY=<your-azure-openai-key>
AZURE_LLM_ENDPOINT=<your-azure-endpoint>
```

## Usage

### Starting the Server

```bash
# Method 1: Via Docker Compose (recommended for production)
docker-compose up -d
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000

# Method 2: Direct execution (development)
python -m uvicorn src.server.server:app --reload --host 0.0.0.0 --port 8000

# Method 3: Python module execution
python -m src.server.server
```

Server will be available at `http://localhost:8000`

### Web Interface (Recommended)

Access the chat interface at **http://localhost:3000** after starting Docker Compose.

Features:

- Real-time streaming chat
- Multiple conversation threads
- SQL query display with syntax highlighting
- Mobile-responsive design
- Local storage for conversation history

See `frontend/README.md` for frontend documentation.

### API Endpoints

#### 1. Streaming Chat (Primary - Server-Sent Events)

**POST** `/chat/stream`

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many emails have been processed?",
    "thread_id": "user-123",
    "anticipate_complexity": false
  }'
```

**Response** (Server-Sent Events):

```
data: {"type": "status", "content": "Executing query..."}
data: {"type": "message", "content": "There are 147 emails in the database."}
data: {"type": "queries", "queries": [{"query": "SELECT COUNT(*) FROM emails_processed", "explanation": "Counts the total number of processed email records", "result_summary": "Found 147 records"}]}
data: {"type": "summary", "content": "Retrieved the total count of emails by querying the emails_processed table"}
data: {"type": "end"}
```

**Event Types:**

- `status`: Processing status updates
- `message`: AI response content
- `queries`: SQL queries with explanations and summaries
- `summary`: Overall workflow summary
- `end`: Stream completion
- `error`: Error messages

#### 2. Non-Streaming Chat (Fallback)

**POST** `/chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many emails have been processed?",
    "thread_id": "user-123",
    "anticipate_complexity": false
  }'
```

**Response:**

```json
{
  "response": "There are 147 emails in the database.",
  "thread_id": "user-123",
  "executed_queries": [
    {
      "query": "SELECT COUNT(*) FROM emails_processed",
      "explanation": "Counts the total number of processed email records",
      "result_summary": "Found 147 records"
    }
  ]
}
```

#### 3. Conversation History

**GET** `/history/{thread_id}`

```bash
curl http://localhost:8000/history/user-123
```

**Response:**

```json
{
  "thread_id": "user-123",
  "history": [
    {
      "checkpoint_id": "abc123",
      "messages": [
        { "type": "HumanMessage", "content": "How many emails?" },
        { "type": "AIMessage", "content": "147 emails" }
      ],
      "timestamp": "2025-11-21T10:30:00",
      "metadata": {}
    }
  ]
}
```

#### 4. Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "westbrand-sql-chat-agent"
}
```

### Request Parameters

**ChatRequest Model:**

- `message` (string, required): User's question
- `thread_id` (string, required): Unique thread identifier for conversation continuity
- `anticipate_complexity` (boolean, optional, default: false):
  - `false`: Direct answers with minimal queries (faster, 10 max iterations)
  - `true`: Thorough exploratory analysis (comprehensive, 30 max iterations)

### Anticipate Complexity Feature

The `anticipate_complexity` parameter controls analysis depth:

**Direct Mode (`false`, default)**:

- Skips question enrichment step
- Maximum 10 query iterations
- Faster execution
- Best for straightforward questions
- Example: "How many emails?" → Direct COUNT query

**Thorough Mode (`true`)**:

- Performs question enrichment with 1-3 sub-questions
- Maximum 30 query iterations
- Comprehensive analysis
- Best for complex, ambiguous questions requiring deep analysis
- Example: "Analyze product trends" → Multiple queries with joins and aggregations

**Implementation:**

- `enrich_question.py`: Skips enrichment if `anticipate_complexity == False`
- `generate_query.py`: Adjusts max query iterations based on setting

**Streamed Response:**

```
data: {"type": "token", "content": "The"}
data: {"type": "token", "content": " top"}
data: {"type": "token", "content": " 5"}
...
data: {"type": "message", "content": "The top 5 products are..."}
data: {"type": "end"}
```

#### 3. Conversation History

**GET** `/history/{thread_id}`

```bash
curl http://localhost:8000/history/user-123
```

**Response:**

```json
{
  "thread_id": "user-123",
  "history": [
    {
      "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c",
      "messages": [
        { "type": "HumanMessage", "content": "How many emails?" },
        { "type": "AIMessage", "content": "There are 147 emails." }
      ],
      "timestamp": "2025-11-19T10:30:00Z",
      "metadata": { "step": 2 }
    }
  ]
}
```

#### 4. Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

## Example Queries

### Database Statistics

```
Q: "How many emails have been processed?"

Enriched Questions:
1. Total count of emails in the database
2. Date range of processed emails
3. Any recent email processing activity

A: "There are 147 emails in the emails_processed table."

📊 SQL Queries Executed:
Query 1:
  💡 Counts the total number of processed email records
  📈 Result: Found 147 records
  SQL: SELECT COUNT(*) FROM emails_processed;
```

```
Q: "How many product mentions are there?"
A: "There are 523 product mentions extracted from emails."

📊 SQL Queries Executed:
Query 1:
  💡 Counts all product mentions in the database
  📈 Result: Found 523 records
  SQL: SELECT COUNT(*) FROM product_mentions;
```

### Product Analysis

```
Q: "What are the top 5 most mentioned products?"
A: "The top 5 products are: Grade 8 Bolts (45 mentions), Stainless Fasteners (32 mentions)..."

📊 SQL Queries Executed:
Query 1:
  💡 Groups products by name and counts mentions to find most frequently requested items
  📈 Result: Found 5 products with mention counts
  SQL: SELECT product_name, COUNT(*) as mentions
       FROM product_mentions
       GROUP BY product_name
       ORDER BY mentions DESC
       LIMIT 5;
```

```
Q: "Which products have no inventory matches?"
A: "Found 23 products without matches..."

📊 SQL Queries Executed:
Query 1:
  💡 Finds products that don't have corresponding inventory matches using a LEFT JOIN
  📈 Result: Found 23 unmatched products
  SQL: SELECT pm.product_name, pm.exact_product_text
       FROM product_mentions pm
       LEFT JOIN inventory_matches im ON pm.id = im.product_mention_id
       WHERE im.id IS NULL
       LIMIT 50;
```

### Match Quality

```
Q: "Show me flagged matches requiring review"
A: "Found 12 matches requiring manual review..."

📊 SQL Queries Executed:
Query 1:
  💡 Retrieves unresolved quality issues by joining flags with product mentions
  📈 Result: Found 12 flagged items
  SQL: SELECT pm.product_name, mrf.issue_type, mrf.reason
       FROM match_review_flags mrf
       JOIN product_mentions pm ON mrf.product_mention_id = pm.id
       WHERE mrf.is_resolved = false
       LIMIT 20;
```

## Testing

### Run All Tests

```bash
# Run all chat workflow tests
pytest tests/chat_workflow/ -v

# Run with coverage
pytest tests/chat_workflow/ --cov=src/chat_workflow --cov-report=html
```

### Test Categories

```bash
# Run specific test files
pytest tests/chat_workflow/test_models.py -v        # Pydantic state models
pytest tests/chat_workflow/test_nodes.py -v         # Individual workflow nodes
pytest tests/chat_workflow/test_graph.py -v         # LangGraph workflow integration

# Current test status: Check with pytest for latest results
```

**Test Coverage Areas:**

- Pydantic v2 state models (`ChatState`, `QuestionEnrichment`, `QueryExplanation`, `QueryExecution`)
- Database utilities and connection management
- Individual workflow nodes (enrich_question, generate_query, execute_query, generate_explanations)
- LangGraph workflow integration and state management
- FastAPI endpoints (streaming and non-streaming)
- Conversation persistence with PostgreSQL checkpointer

## File Structure

```
src/chat_workflow/
├── __init__.py                  # Module exports
├── cli.py                       # Interactive CLI interface
├── graph.py                     # LangGraph workflow definition with 4 nodes
├── prompts.py                   # WestBrand system prompts and schemas
├── README.md                    # This file
├── nodes/
│   ├── __init__.py
│   ├── enrich_question.py       # Expand user questions for better context
│   ├── generate_query.py        # Natural language → SQL with tool binding
│   ├── execute_query.py         # Validate and execute SELECT queries
│   └── generate_explanations.py # Create AI explanations for queries
└── utils/
    ├── __init__.py
    ├── db_wrapper.py            # PostgreSQL connection setup
    └── tools.py                 # LangChain tools (run_query_tool, get_schema_tool)

src/models/
└── chat_models.py               # Pydantic v2 models
    ├── ChatState                # LangGraph state with message history
    ├── QuestionEnrichment       # Enriched question details
    ├── QueryExplanation         # Query explanation and summary
    └── QueryExecution           # Individual query execution details

tests/chat_workflow/
├── test_models.py               # Pydantic model tests
├── test_nodes.py                # Individual node tests
├── test_graph.py                # Workflow integration tests
└── fixtures/                    # Test data
```

├── test_list_tables.py
├── test_execute_query.py
├── test_graph.py
└── test_api.py

````

## Safety Features

### Read-Only Enforcement

All queries are validated before execution:

- ✅ SELECT queries allowed
- ❌ INSERT, UPDATE, DELETE rejected
- ❌ DROP, ALTER, CREATE rejected
- ❌ TRUNCATE, GRANT, REVOKE rejected

### Table Whitelisting

Only WestBrand tables accessible:

- `emails_processed`
- `product_mentions`
- `inventory_items`
- `inventory_matches`
- `match_review_flags`

### Result Limiting

- Default `LIMIT 100` in system prompt
- Prevents accidentally returning huge datasets

## Conversation Persistence

Conversations are stored in PostgreSQL using LangGraph's `PostgresSaver`:

### Checkpoint Tables

The checkpointer automatically creates:

- `checkpoints`: Stores conversation states
- `checkpoint_writes`: Stores intermediate writes

### Thread Management

Each conversation has a unique `thread_id`:

- Client-generated UUIDs
- Maintains context across sessions
- Retrievable via `/history/{thread_id}`

## Integration with WestBrand System

### Database Schema Awareness

The agent has built-in knowledge of:

- Table relationships (emails → products → matches)
- Foreign key structure (thread_hash, product_mention_id)
- JSON property columns
- Common query patterns

### LLM Configuration

Uses existing `get_llm_client()` from `src/llm/client.py`:

- Model: Azure OpenAI gpt-4.1
- Temperature: 0 (deterministic)
- Reasoning effort: low
- Cached singleton pattern

## Development

### Adding New Endpoints

1. Define request/response models with Pydantic
2. Add endpoint to `api.py`
3. Write tests in `test_api.py`
4. Update this README

### Modifying Workflow

1. Update nodes in `src/chat_workflow/nodes/`
2. Modify `graph.py` if adding/removing nodes
3. Update tests
4. Verify with `pytest tests/chat_workflow/`

### Updating System Prompts

Edit `src/chat_workflow/prompts.py`:

- `WESTBRAND_SYSTEM_PROMPT`: Main agent instructions
- Include table schemas, relationships, common queries

## Troubleshooting

### "DATABASE_URL not set" Error

**Solution**: Add `DATABASE_URL` to `.env` file

### "No module named 'langgraph.checkpoint.postgres'"

**Solution**: Install checkpoint package:

```bash
pip install langgraph-checkpoint-postgres
````

### Checkpointer Setup Fails

**Solution**: Ensure PostgreSQL is running:

```bash
docker-compose up -d
```

### Tests Fail with Connection Error

**Solution**: Tests use mocks, but check DATABASE_URL format:

```bash
postgresql://user:password@host:port/database
```

## Future Enhancements

### Planned Features

- [ ] Query result export to CSV/Excel
- [ ] Advanced query optimization suggestions
- [ ] Visual query plan display
- [ ] Query history search across all threads
- [ ] User authentication/authorization
- [ ] Rate limiting per thread_id

### Performance Optimizations

- [x] Redis LLM response caching (implemented)
- [x] PostgreSQL conversation persistence (implemented)
- [ ] Connection pooling for database queries
- [ ] Response compression for large result sets
- [ ] Parallel query execution for independent queries
- [ ] Query result caching with TTL

## License

Part of the WestBrand Email Analysis System.

## Support

For issues or questions:

1. Check test coverage: `pytest tests/chat_workflow/ -v`
2. Review logs in FastAPI console
3. Check LangSmith traces (if configured)
4. Review `.github/copilot-instructions.md` for system details
