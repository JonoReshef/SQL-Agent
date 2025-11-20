# WestBrand SQL Chat Agent

A natural language interface to the WestBrand database using LangGraph and FastAPI.

## Overview

The SQL Chat Agent allows users to query the WestBrand PostgreSQL database using natural language. It uses Azure OpenAI GPT-5 to convert questions into SQL queries, execute them safely (read-only), and return formatted results.

## Architecture

### Technology Stack

- **LangGraph**: State management and workflow orchestration
- **FastAPI**: REST API with streaming support
- **Azure OpenAI GPT-5**: Natural language to SQL conversion
- **PostgreSQL**: Database backend with conversation persistence
- **Pydantic v2**: Type-safe state models

### Workflow Nodes

1. **List Tables**: Discovers available database tables
2. **Get Schema**: Fetches detailed table schemas
3. **Generate Query**: Converts natural language to SQL
4. **Execute Query**: Runs validated SELECT queries
5. **Loop**: Supports multi-turn conversations

### Key Features

- ✅ **Read-only access**: Only SELECT queries allowed
- ✅ **Conversation persistence**: PostgreSQL-based checkpointing
- ✅ **Streaming responses**: Server-Sent Events (SSE)
- ✅ **Multi-turn conversations**: Maintains context across queries
- ✅ **Domain knowledge**: WestBrand-specific system prompts
- ✅ **Type-safe**: Pydantic models with full validation
- ✅ **Test coverage**: 51/51 tests passing

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database running (Docker)
- Azure OpenAI API access

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
DATABASE_URL=postgresql://westbrand:westbrand_pass@localhost:5432/westbrand_db
AZURE_LLM_API_KEY=<your-azure-openai-key>
AZURE_LLM_ENDPOINT=<your-azure-endpoint>
```

## Usage

### Starting the Server

```bash
# Method 1: Direct execution
python -m src.chat_workflow.api

# Method 2: Using uvicorn
uvicorn src.chat_workflow.api:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`

### API Endpoints

#### 1. Non-Streaming Chat

**POST** `/chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many emails have been processed?",
    "thread_id": "user-123"
  }'
```

**Response:**

```json
{
  "response": "There are 147 emails in the database.",
  "thread_id": "user-123"
}
```

#### 2. Streaming Chat (SSE)

**POST** `/chat/stream`

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 most mentioned products?",
    "thread_id": "user-123"
  }'
```

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
A: "There are 147 emails in the emails_processed table."

Q: "How many product mentions are there?"
A: "There are 523 product mentions extracted from emails."
```

### Product Analysis

```
Q: "What are the top 5 most mentioned products?"
A: SQL: SELECT product_name, COUNT(*) as mentions
       FROM product_mentions
       GROUP BY product_name
       ORDER BY mentions DESC
       LIMIT 5;

   Top products: Grade 8 Bolts (45), Stainless Fasteners (32)...

Q: "Which products have no inventory matches?"
A: SQL: SELECT pm.product_name
       FROM product_mentions pm
       LEFT JOIN inventory_matches im ON pm.id = im.product_mention_id
       WHERE im.id IS NULL
       LIMIT 10;
```

### Match Quality

```
Q: "Show me flagged matches requiring review"
A: SQL: SELECT pm.product_name, mrf.issue_type, mrf.reason
       FROM match_review_flags mrf
       JOIN product_mentions pm ON mrf.product_mention_id = pm.id
       WHERE mrf.is_resolved = false
       LIMIT 10;
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

- **test_models.py**: Pydantic state models (6 tests)
- **test_db_wrapper.py**: Database utilities (14 tests)
- **test_list_tables.py**: Table discovery node (4 tests)
- **test_execute_query.py**: Query execution node (9 tests)
- **test_graph.py**: LangGraph workflow (7 tests)
- **test_api.py**: FastAPI endpoints (11 tests)

**Total: 51/51 tests passing ✅**

## File Structure

```
src/chat_workflow/
├── __init__.py           # Exports for module
├── api.py                # FastAPI server with 4 endpoints
├── graph.py              # LangGraph workflow definition
├── models.py             # Pydantic ChatState model
├── prompts.py            # WestBrand system prompts
├── nodes/
│   ├── list_tables.py    # Discover tables
│   ├── get_schema.py     # Fetch schemas
│   ├── generate_query.py # NL → SQL
│   └── execute_query.py  # Run SQL safely
└── utils/
    ├── db_wrapper.py     # SQLDatabase setup
    └── __init__.py

tests/chat_workflow/
├── test_models.py
├── test_db_wrapper.py
├── test_list_tables.py
├── test_execute_query.py
├── test_graph.py
└── test_api.py
```

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

- Model: Azure OpenAI GPT-5
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
```

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

- [ ] Query result caching (Redis)
- [ ] Rate limiting per thread_id
- [ ] User authentication/authorization
- [ ] Query cost estimation
- [ ] Multi-database support
- [ ] Query history search
- [ ] Export results to CSV/Excel

### Performance Optimizations

- [ ] Connection pooling
- [ ] Response compression
- [ ] Async database queries
- [ ] LLM response caching

## License

Part of the WestBrand Email Analysis System.

## Support

For issues or questions:

1. Check test coverage: `pytest tests/chat_workflow/ -v`
2. Review logs in FastAPI console
3. Check LangSmith traces (if configured)
4. Review `.github/copilot-instructions.md` for system details
