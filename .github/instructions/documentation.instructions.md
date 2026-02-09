---
description: Guidelines for maintaining documentation and README files
applyTo: '**/{README.md,*.md}'
excludeAgent: ['code-review']
---

# Documentation Guidelines

## Critical Requirement

**Every directory MUST have a README.md file**. This is a fundamental requirement for repository organization.

## README.md Structure

Each directory's README.md must include these three sections:

### 1. Purpose

A brief (1-3 sentences) description of what the code in this directory is intended to achieve.

Example:

```markdown
**Purpose**:
This directory contains the backend API implementation for the AI testing platform. It handles workflow execution, database interactions, and API endpoints.
```

### 2. Content

A list of the main components, modules, or features included in this directory.

Example:

```markdown
**Content**:

- API route handlers (`/routes`)
- Database models and migrations (`/models`)
- LangGraph workflow definitions (`/workflows`)
- Service layer for business logic (`/services`)
- Configuration and settings (`config.py`)
```

### 3. Technical Constraints

Specific technologies, frameworks, versions, or requirements used in this directory.

Example:

```markdown
**Technical Constraints**:

- Python 3.13 with virtual environment in `.venv`
- Pydantic v2 for data validation
- LangGraph for AI workflow orchestration
- PostgreSQL 17+ for database
- FastAPI for REST API framework
```

## When to Update README Files

Update the README.md whenever:

- ✅ Adding new files or modules to a directory
- ✅ Removing or renaming major components
- ✅ Changing technology stack or versions
- ✅ Adding new dependencies or requirements
- ✅ Restructuring the directory layout
- ✅ Changing the purpose or scope of the directory

## Example Complete README

```markdown
**Purpose**:
This directory contains the frontend application built with Next.js and React. It provides the user interface for interacting with AI workflows and viewing results.

**Content**:

- Next.js App Router pages (`/app`)
- Reusable React components (`/components`)
- API integration services (`/services`)
- TypeScript type definitions (`/types`)
- Custom React hooks (`/hooks`)
- Utility functions (`/lib`)

**Technical Constraints**:

- TypeScript with strict mode enabled
- Next.js 16+ with App Router
- React 19
- Node.js 18+
- Type definitions must stay synchronized with backend Pydantic models
```

## Documentation Best Practices

### Use Clear Language

- Write for both humans and AI assistants
- Be specific about requirements and constraints
- Use active voice
- Avoid ambiguous terms

### Keep It Updated

- README files should reflect current reality
- Remove outdated information promptly
- Document workarounds and known issues

### Cross-Reference When Needed

- Link to related documentation
- Reference specific files when helpful
- Point to external documentation for dependencies

Example:

```markdown
For API endpoint documentation, see [API.md](./API.md).
For LangGraph workflow patterns, refer to the [official LangGraph documentation](https://langchain-ai.github.io/langgraph/).
```

## Repository Root README

The root README.md should provide:

- High-level project overview
- Quick start instructions
- Links to detailed documentation
- Project goals and scope
- Repository structure overview

## Code Documentation

### Python Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def execute_workflow(workflow_id: str, parameters: dict[str, any]) -> WorkflowResult:
    """
    Execute an AI workflow with the given parameters.

    Args:
        workflow_id: Unique identifier for the workflow to execute
        parameters: Dictionary of parameters to pass to the workflow

    Returns:
        WorkflowResult containing execution status and output

    Raises:
        WorkflowNotFoundError: If the workflow_id doesn't exist
        ValidationError: If parameters are invalid
    """
    pass
```

### TypeScript/JSDoc Comments

Use JSDoc for complex functions or exported utilities:

```typescript
/**
 * Executes a workflow via the API
 *
 * @param request - Workflow execution request including ID and parameters
 * @returns Promise resolving to the workflow execution response
 * @throws {ApiError} When the API request fails
 */
export async function executeWorkflow(
  request: WorkflowRequest
): Promise<WorkflowResponse> {
  // Implementation
}
```

## Changelog Practices

If maintaining a CHANGELOG.md:

- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Group changes: Added, Changed, Deprecated, Removed, Fixed, Security
- Include version numbers and dates
- Write for end users, not developers

## Common Mistakes to Avoid

❌ **Don't**: Leave directories without README files
✅ **Do**: Create README.md for every new directory

❌ **Don't**: Write overly technical README content
✅ **Do**: Balance technical detail with accessibility

❌ **Don't**: Let documentation drift from code
✅ **Do**: Update docs in the same commit as code changes

❌ **Don't**: Copy-paste README content between directories
✅ **Do**: Write specific, relevant content for each directory

❌ **Don't**: Document temporary or trivial implementation details
✅ **Do**: Focus on architecture, requirements, and key patterns

## Validation Checklist

Before committing, verify:

- [ ] Every modified directory has an up-to-date README.md
- [ ] README includes all three required sections (Purpose, Content, Technical Constraints)
- [ ] Technical constraints reflect current technology versions
- [ ] Content list matches actual directory structure
- [ ] Purpose accurately describes the directory's role
- [ ] Language is clear and specific
- [ ] No outdated information remains
