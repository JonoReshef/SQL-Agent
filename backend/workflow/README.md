# Backend Workflow - Email Analysis Pipeline

## Purpose

Email analysis workflow that processes `.msg` files to extract product mentions, match them against inventory using hierarchical filtering, persist data to PostgreSQL, and generate Excel reports.

## Content

- **analysis_workflow/** - LangGraph workflow for email analysis
  - `graph.py` - Main workflow definition with 5 nodes
  - `utils.py` - Email parsing utilities
  - `nodes/` - Individual workflow nodes
    - `ingestion/` - Load and parse .msg files
    - `extraction/` - Extract products using LLM
    - `matching/` - Hierarchical inventory matching
    - `persistence/` - Store to database
    - `reporting/` - Generate Excel reports

- **inventory/** - Inventory management
  - `loader.py` - Load inventory from Excel
  - `parser.py` - Parse inventory descriptions with LLM
  - `import_inventory.py` - CLI to import inventory to database

- **models/** - Pydantic data models
  - `email.py` - Email, EmailMetadata
  - `product.py` - ProductMention, ProductProperty, ProductAnalytics
  - `inventory.py` - InventoryItem, InventoryMatch, ReviewFlag
  - `configs.py` - ProductConfig, PropertyDefinition
  - `analysis_workflow.py` - WorkflowState for LangGraph

- **database/** - Database utilities (shared module copy)
- **llm/** - Azure OpenAI client wrapper (shared module copy)
- **config/** - Configuration loader (shared module copy)
- **utils/** - Utility functions
- **main.py** - CLI entry point for email analysis
- **tests/** - Pytest test suite

## Technical Constraints

- **Python 3.13** required
- **Azure OpenAI** (gpt-5 with low reasoning) for extraction
- **PostgreSQL 17** for data storage
- **Redis** for LLM response caching
- Processes `.msg` files synchronously
- Uses hierarchical property filtering for fast inventory matching

## Running

```bash
# Run email analysis
python -m backend_workflow.main --input-dir data/emails --output-dir output

# Run tests
pytest backend_workflow/tests/ -v
```

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string (for caching)
- `AZURE_LLM_API_KEY` - Azure OpenAI API key
- `AZURE_LLM_ENDPOINT` - Azure OpenAI endpoint
