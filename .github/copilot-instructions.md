# WestBrand Email Analysis System - AI Agent Instructions

## System Overview

This is a **synchronous, test-driven Python system** that analyzes Outlook `.msg` emails to extract industrial product information and generate Excel reports. The system uses **Azure OpenAI (GPT-5)** orchestrated through **LangGraph** workflows.

## Key instructions

- Follow a test driven development method by running and building unit tests as code is changed or created
- Update documentation and these instructions whenever there are material changes to the product
- When there are complex new capabilities created, make specific markdown instructions which can be referenced which explain how the system works and how to use it

### Core Architecture Principles

- **No async/await**: All operations are synchronous for simplicity. Use `llm.invoke()`, NOT `.ainvoke()`
- **No email threading**: Each `.msg` file is analyzed independently. Do NOT attempt thread reconstruction
- **Test-first approach**: Write tests before implementation. 26+ tests currently passing
- **Type safety**: All data structures use Pydantic v2 models with strict validation

## Critical Workflows

### Running the System

```bash
# Start Redis cache (required for LLM caching)
docker-compose up -d

# Run analysis (from project root)
python -m src.main

# Or with custom paths
python -m src.main data/custom/ output/report.xlsx
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
```

LLM client is a **cached singleton** (`@lru_cache`) in `src/llm/client.py`. Configuration:

- Deployment: `gpt-5`
- API Version: `2024-08-01-preview`
- Temperature: 0 (deterministic)
- Reasoning effort: `low`

## LangGraph Workflow Architecture

### State Machine Flow

```
Ingestion Node → Extraction Node → Reporting Node
```

**State structure** (`WorkflowState` Pydantic model):

```python
{
    "input_directory": str,
    "emails": List[Email],
    "extracted_products": List[ProductMention],
    "analytics": List[ProductAnalytics],
    "report_path": str,
    "errors": List[str]  # Default: [] (auto-initialized)
}
```

### Node Responsibilities

- **Ingestion** (`src/workflow/nodes/ingestion.py`): Load `.msg` files, parse with `extract-msg`, clean signatures/HTML
- **Extraction** (`src/workflow/nodes/extraction.py`): Call Azure OpenAI to extract products using structured output
- **Reporting** (`src/workflow/nodes/reporting.py`): Generate multi-sheet Excel with openpyxl

**Redis caching** is enabled in `graph.py` via `langchain_redis.RedisCache` to reduce redundant LLM calls.

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

# workflow.py
WorkflowState: Pydantic BaseModel for LangGraph state management (with default values)
```

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

Generates 3-sheet workbook:

1. **Product Mentions**: Detailed per-mention data
2. **Analytics**: Aggregated metrics by product
3. **Email Summary**: Per-email metadata and product counts

Features: Auto-filter, frozen panes, conditional formatting, date formatting

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

## Common Pitfalls to Avoid

1. **Don't use async**: This codebase is intentionally synchronous
2. **Don't attempt email threading**: Out of scope by design
3. **Don't skip preprocessing**: HTML removal is critical for LLM accuracy
4. **Don't modify product config without updating extractors**: Config and prompts are tightly coupled
5. **Don't forget Redis**: LLM caching requires `docker-compose up` for Redis
6. **Don't use old Pydantic syntax**: This is v2 (use `ConfigDict`, not `Config`)

## Integration Points

### External Dependencies

- **Azure OpenAI**: All LLM calls go through `get_llm_client()` singleton
- **Redis**: Required for LangChain caching (`redis://localhost:6379`)
- **LangGraph**: State management and workflow orchestration

### Data Flow

```
.msg files → extract-msg → BeautifulSoup (cleaning) →
LangGraph state → Azure OpenAI (structured output) →
Pydantic models → openpyxl → Excel report
```

## Debugging Tips

- Check Redis is running: `docker ps` should show `westbrand-redis`
- Validate `.env` variables: `echo $AZURE_LLM_API_KEY`
- Run single tests: `pytest tests/test_extractors.py::TestClassName::test_method -v`
- Inspect LangGraph state: Add print statements in node functions
- Check LLM responses: Set `verbose=True` in `client.py` temporarily

## Future Considerations (from NOTES.md)

- Email linking in reports for source grounding
- Better email export formats from Outlook/Gmail
- Unique product extraction per email thread (currently extracts all mentions)
