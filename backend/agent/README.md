# Backend Agent - SQL Chat Agent

## Purpose

Natural language SQL chat agent that allows users to query the WestBrand database using plain English. Uses LangGraph to orchestrate a multi-step workflow that enriches questions, generates SQL queries, executes them safely, and provides explanations.

## Content

- **chat_workflow/** - LangGraph workflow for SQL chat
  - `graph.py` - Main workflow definition with 4 nodes
  - `prompts.py` - System prompts for SQL generation
  - `cli.py` - Command-line interface for testing
  - `nodes/` - Individual workflow nodes
  - `utils/` - Database wrapper and LangChain tools

- **server/** - FastAPI REST API server
  - `server.py` - Endpoints: `/chat`, `/chat/stream`, `/history/{thread_id}`

- **models/** - Pydantic data models
  - `chat_models.py` - ChatState, QueryExecution, QueryExplanation
  - `server.py` - ChatRequest, ChatResponse, HistoryResponse

- **database/** - Database utilities (shared module copy)
- **llm/** - Azure OpenAI client wrapper (shared module copy)
- **tests/** - Pytest test suite

## Technical Constraints

- **Python 3.13** required
- **Azure OpenAI** (gpt-4.1) for SQL generation
- **PostgreSQL 17** for data storage and LangGraph checkpointer
- **Redis** for LLM response caching
- **Read-only** SQL queries only (SELECT statements)
- Uses LangChain's SQLDatabase for query execution

## Running

```bash
# Start server
uvicorn backend_agent.server.server:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest backend_agent/tests/ -v
```

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string (optional, for caching)
- `AZURE_LLM_API_KEY` - Azure OpenAI API key
- `AZURE_LLM_ENDPOINT` - Azure OpenAI endpoint
