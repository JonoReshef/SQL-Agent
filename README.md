# WestBrand Email Analysis System

## Overview

A Python-based system for analyzing emails (`.msg` files) to extract product mentions and generate Excel reports for business analysis. The system uses AI (Azure OpenAI) orchestrated through LangGraph to identify products, their properties, and contextual information from email communications.

## Updated Architecture (November 2025)

### Key Design Decisions

1. **No Thread Reconstruction**: Each `.msg` file is analyzed as a single entity. No email threading or conversation reconstruction is performed.
2. **Synchronous Processing**: All operations are synchronous (no async/await) for simplicity. LLM calls use `.invoke()` not `.ainvoke()`.
3. **Test-Driven Development**: Comprehensive unit and integration tests written before implementation using `pytest`.
4. **Extract-msg Library**: Using `extract-msg` (already in dependencies) instead of `mail-parser` for parsing Outlook `.msg` files.

### Technology Stack

| Component            | Technology      | License | Purpose                             |
| -------------------- | --------------- | ------- | ----------------------------------- |
| **Email Parsing**    | extract-msg     | MIT     | Parse Outlook .msg files            |
| **HTML Processing**  | BeautifulSoup4  | MIT     | Strip HTML from email bodies        |
| **AI Orchestration** | LangGraph       | MIT     | State machine workflow              |
| **LLM**              | AzureChatOpenAI | MIT     | Product extraction via Azure OpenAI |
| **Data Models**      | Pydantic v2     | MIT     | Type-safe data structures           |
| **Configuration**    | PyYAML          | MIT     | Product config management           |
| **Excel Output**     | openpyxl        | MIT     | Generate Excel reports              |
| **Testing**          | pytest          | MIT     | Unit & integration tests            |

## Project Structure

```
WestBrand/
├── config/
│   └── products_config.yaml        # Product definitions & extraction rules
├── src/
│   ├── models/
│   │   ├── email.py                # Email & EmailMetadata models
│   │   ├── product.py              # ProductMention & ProductAnalytics models
│   │   └── workflow.py             # LangGraph state models
│   ├── email_processor/
│   │   ├── msg_reader.py           # ✅ Parse .msg files
│   │   └── signature_cleaner.py    # ✅ Remove signatures/HTML
│   ├── workflow/
│   │   ├── graph.py                # LangGraph workflow definition
│   │   └── nodes/
│   │       ├── ingestion.py        # Load and parse emails
│   │       ├── extraction.py       # Extract products with LLM
│   │       └── reporting.py        # Generate Excel report
│   ├── llm/
│   │   ├── client.py               # Azure OpenAI client wrapper
│   │   └── extractors.py          # Product extraction logic
│   ├── report/
│   │   └── excel_generator.py     # Multi-sheet Excel generation
│   ├── config/
│   │   └── config_loader.py       # Load YAML configuration
│   └── main.py                    # Entry point
├── tests/
│   ├── test_msg_reader.py         # ✅ 13 tests passing
│   ├── test_signature_cleaner.py  # ✅ 13 tests passing
│   ├── test_workflow.py           # Workflow tests
│   ├── test_extractors.py         # LLM extraction tests
│   ├── test_report.py             # Excel generation tests
│   └── test_integration.py        # End-to-end tests
├── data/                          # Email .msg files
├── output/                        # Generated Excel reports
├── .env                           # Azure credentials
├── requirements.txt               # ✅ Dependencies installed
├── pyproject.toml                 # ✅ Pytest configuration
└── README.md                      # This file
```

## Completed Components ✅

### 1. Email Parser (`src/email_processor/msg_reader.py`)

- ✅ Parses Outlook `.msg` files using `extract-msg`
- ✅ Extracts metadata (subject, sender, recipients, date)
- ✅ Handles multiple body formats (plain text, HTML, RTF)
- ✅ Lists attachments
- ✅ Returns typed `Email` Pydantic model
- ✅ **13 unit tests passing**

### 2. Signature Cleaner (`src/email_processor/signature_cleaner.py`)

- ✅ Strips HTML tags using BeautifulSoup
- ✅ Removes email signatures and footers
- ✅ Removes quoted reply text (>)
- ✅ Removes forwarded message headers
- ✅ Preserves main email content
- ✅ **13 unit tests passing**

### 3. Pydantic Models (`src/models/`)

- ✅ `Email` and `EmailMetadata` - Email data structures
- ✅ `ProductMention` and `ProductProperty` - Product extraction
- ✅ `ProductAnalytics` - Aggregated metrics
- ✅ Updated to Pydantic v2 syntax (ConfigDict)

## Workflow Design

```
┌─────────────────────────────────────────────────────────────┐
│                  Configuration Layer                         │
│         products_config.yaml (products & properties)         │
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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Ingestion  │→ │  Extraction  │→ │   Reporting  │      │
│  │    Node      │  │     Node     │  │     Node     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  • Parse .msg     • Clean body      • Aggregate data        │
│  • Clean HTML     • LLM extract     • Generate Excel        │
│                   • Validate                                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     Output Layer                             │
│              Excel Workbook (3 sheets)                       │
│    1. Product Mentions | 2. Analytics | 3. Summary          │
└─────────────────────────────────────────────────────────────┘
```

## Azure OpenAI Configuration

```python
from langchain_openai import AzureChatOpenAI
import os

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_LLM_API_KEY"),
    azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
    azure_deployment="gpt-4.1",
    api_version="",
    verbose=False,
    temperature=0,  # Deterministic for extraction
)
```

### Environment Variables Required

Create a `.env` file:

```bash
AZURE_LLM_API_KEY=your_api_key_here
AZURE_LLM_ENDPOINT=https://your-endpoint.openai.azure.com/
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

### Sheet 1: Product Mentions

| Product | Category | Properties | Quantity | Unit | Context | Date Requested | Email Subject | Sender | Email Date | File |
| ------- | -------- | ---------- | -------- | ---- | ------- | -------------- | ------------- | ------ | ---------- | ---- |

### Sheet 2: Analytics

| Product | Category | Total Mentions | First Mention | Last Mention | Total Quantity | Unique Properties |
| ------- | -------- | -------------- | ------------- | ------------ | -------------- | ----------------- |

### Sheet 3: Email Summary

| Email File | Subject | Sender | Date | Products Mentioned | Has Attachments |
| ---------- | ------- | ------ | ---- | ------------------ | --------------- |

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

```bash
# Basic usage
python -m src.main data/sales@westbrand.ca output/report.xlsx

# With specific directory (recursive)
python -m src.main data/sales@westbrand.ca/Recoverable-Items output/detailed_report.xlsx

# With custom config
python -m src.main data/emails output/report.xlsx --config config/custom_products.yaml
```

## Development Workflow

1. **Write Tests First**: Before implementing any feature, write comprehensive unit tests
2. **Run Tests Frequently**: Execute tests after each change
3. **Keep It Synchronous**: No async code - use `.invoke()` for LLM calls
4. **Single Email Processing**: Each `.msg` file is independent - no threading
5. **Type Safety**: All data uses Pydantic models for validation

## Next Steps (In Order)

1. **Configuration System** - Load products_config.yaml
2. **LangGraph Workflow** - Build state machine with nodes
3. **LLM Product Extraction** - Implement extraction with Azure OpenAI
4. **Excel Report Generator** - Create multi-sheet workbooks
5. **Main Entry Point** - Orchestrate full workflow
6. **Integration Tests** - End-to-end testing

## Testing Strategy

- ✅ **Unit Tests**: Individual components (msg_reader, signature_cleaner)
- 🔄 **Integration Tests**: Component interactions (workflow, extraction)
- 🔄 **End-to-End Tests**: Full workflow from .msg to Excel
- **Mocking**: Mock Azure OpenAI responses for deterministic tests
- **Fixtures**: Sample .msg files and expected outputs

## Performance Notes

- Performance is not a priority in this phase
- Synchronous processing keeps code simple and debuggable
- Can process ~10-20 emails/minute (depends on LLM latency)
- No caching or optimization implemented yet

## License

All dependencies use permissive licenses (MIT, Apache 2.0, BSD)

---

**Status**: Foundation Complete (26/26 tests passing)
**Last Updated**: November 12, 2025
