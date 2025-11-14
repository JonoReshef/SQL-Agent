# WestBrand Email Analysis - Architectural Overview

## Executive Summary

A test-driven Python system for analyzing Outlook emails to extract product information and generate Excel reports. The system processes individual `.msg` files (no threading), uses Azure OpenAI for intelligent extraction, and is orchestrated via LangGraph workflows.

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
┌────────────────────────────────────────────────────────────────┐
│                  LANGGRAPH WORKFLOW (Synchronous)               │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  INGESTION NODE │→ │ EXTRACTION NODE │→ │ REPORTING NODE  ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
│                                                                 │
│  Ingestion:           Extraction:           Reporting:          │
│  • Load .msg files    • Clean body text    • Aggregate data    │
│  • Parse metadata     • LLM invoke()       • Format tables     │
│  • Initial validation • Extract products   • Generate Excel    │
│                       • Validate results    • Apply formatting  │
│                                                                 │
│  State Machine (Pydantic BaseModel):                            │
│  {                                                              │
│    emails: List[Email] = [],                                    │
│    cleaned_emails: List[str] = [],                              │
│    extracted_products: List[ProductMention] = [],               │
│    analytics: List[ProductAnalytics] = [],                      │
│    report_path: str = "",                                       │
│    errors: List[str] = []  # Auto-initialized                   │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                 AI EXTRACTION LAYER                             │
│                  (Azure OpenAI GPT-4.1)                         │
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
  • product_name: str
  • product_category: str
  • properties: List[ProductProperty]
  • quantity: Optional[int]
  • unit: Optional[str]
  • context: str (quote_request, order, inquiry)
  • date_requested: Optional[datetime]
  • email_subject: str
  • email_sender: str
  • email_date: Optional[datetime]
  • email_file: Optional[str]

ProductAnalytics
  • product_name: str
  • product_category: str
  • total_mentions: int
  • first_mention: Optional[datetime]
  • last_mention: Optional[datetime]
  • total_quantity: Optional[int]
  • properties_summary: Dict[str, List[str]]
  • contexts: List[str]
```

## Technology Stack Justification

### Why These Libraries?

1. **extract-msg** (vs mail-parser)

   - ✅ Already in requirements.txt
   - ✅ Specifically for Outlook .msg files
   - ✅ Handles RTF, HTML, plain text bodies
   - ✅ Extracts attachments and metadata
   - ❌ mail-parser: Not maintained since 2020, for standard email formats

2. **LangGraph** (vs raw LangChain)

   - ✅ State machine workflow management
   - ✅ Easy node composition
   - ✅ Built-in error handling
   - ✅ Synchronous execution support
   - ✅ Visual workflow representation

3. **BeautifulSoup4** (vs regex only)

   - ✅ Robust HTML parsing
   - ✅ Handles malformed HTML
   - ✅ Easy tag removal
   - ✅ Entity decoding
   - ✅ Preserves text content

4. **Pydantic v2** (vs dataclasses)

   - ✅ Runtime validation
   - ✅ JSON serialization
   - ✅ Type coercion
   - ✅ Documentation via models
   - ✅ OpenAPI integration ready

5. **openpyxl** (vs pandas/xlsxwriter)
   - ✅ Pure Python (no external deps)
   - ✅ Rich formatting support
   - ✅ Multiple sheet management
   - ✅ Formula support
   - ✅ Active maintenance

## Workflow Execution Flow

```
1. INITIALIZATION
   ├─ Load products_config.yaml
   ├─ Initialize Azure OpenAI client
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
   ├─ Parse JSON response
   ├─ Validate ProductMention models
   └─ Add to state.extracted_products

5. ANALYTICS PHASE
   ├─ Group products by name/category
   ├─ Calculate aggregates:
   │  ├─ Total mentions
   │  ├─ Date ranges
   │  ├─ Quantity sums
   │  └─ Property variations
   └─ Create ProductAnalytics models

6. REPORTING PHASE
   ├─ Create Excel workbook (openpyxl)
   ├─ Generate Sheet 1: Product Mentions
   ├─ Generate Sheet 2: Analytics
   ├─ Generate Sheet 3: Email Summary
   ├─ Apply formatting and filters
   └─ Save to output directory

7. ERROR HANDLING
   ├─ Log parsing errors (continue processing)
   ├─ Record LLM failures
   ├─ Track validation failures
   └─ Generate error report in Excel
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
5. ❌ Database storage (Excel output only)
6. ❌ Multi-language support (English only)

## Deployment Requirements

**System Requirements**:

- Python 3.11+
- 2GB RAM minimum
- 100MB disk space
- Internet connection (Azure OpenAI)

**Dependencies**: See `requirements.txt`

- extract-msg==0.55.0
- beautifulsoup4==4.13.5
- langgraph==1.0.3
- langchain-openai==1.0.2
- pydantic==2.12.4
- openpyxl==3.1.5
- pytest==9.0.1
- pyyaml==6.0.3

## Success Metrics

**Phase 1 (Current)**: Foundation ✅

- [x] 26/26 tests passing
- [x] Email parsing working
- [x] Signature cleaning implemented
- [x] Pydantic models defined

**Phase 2 (Next)**: Core Workflow 🔄

- [ ] LangGraph workflow implemented
- [ ] Azure OpenAI integration working
- [ ] Product extraction functional
- [ ] Configuration system complete

**Phase 3 (Final)**: Production Ready 📋

- [ ] Excel report generation
- [ ] Integration tests passing
- [ ] End-to-end workflow complete
- [ ] Documentation finalized

---

**Document Version**: 1.0  
**Last Updated**: November 12, 2025  
**Status**: Foundation Complete
