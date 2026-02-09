---
description: Guidelines for developing AI workflows with LangGraph
applyTo: 'backend/**/{workflows,agents,*.workflow.py,*.agent.py}'
---

## LangGraph AI Workflow Guidelines

- Define all types and states using pydantic models
- Add comments and docstrings to explain the purpose of each node and edge
- Handle errors gracefully at every node
- Test nodes individually and workflows end-to-end
- Use meaningful node and edge names
- Log important state changes
- Build simple systems first and validate they work before adding complexity
- Implement langgraph persistence/checkpointers using SQLite (for development purposes)
- Implement proper logging and monitoring
- Set timeouts for LLM calls and long-running operations
- Use connection pooling for external services
- Refer to `backend-python.instructions.md` for details on Python development guidelines and `backend-python-testing.instructions.md` for testing guidelines
