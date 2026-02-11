# WestBrand Project

## Architecture

- **Backend**: Python FastAPI + LangGraph agent at `backend/agent/server/server.py`
- **Frontend**: Next.js with TypeScript at `frontend/`
- **DB**: SQLAlchemy ORM with `ChatThread` and `ChatMessageRecord` models
- **Types**: Frontend types in `frontend/types/interfaces.ts`, server types auto-generated from OpenAPI

## Documentation Guidelines

**Every directory MUST have a README.md file** with these three sections:

### Required README Sections

1. **Purpose**: 1-3 sentences describing what the code in this directory achieves
2. **Content**: List of main components, modules, or features
3. **Technical Constraints**: Technologies, frameworks, versions, or requirements used

### When to Update README Files

- Adding new files or modules to a directory
- Removing or renaming major components
- Changing technology stack or versions
- Adding new dependencies or requirements
- Restructuring the directory layout

### Documentation Practices

- Write for both humans and AI assistants
- Be specific about requirements and constraints
- Update docs in the same commit as code changes
- Use Google-style docstrings for Python, JSDoc for complex TypeScript functions
- Do not document temporary or trivial implementation details
- Cross-reference related documentation when helpful
