---
description: Python development guidelines
applyTo: 'backend/**/*.py'
---

## Development instructions

- Always use the existing virtual environment by activating it with `source .venv/bin/activate` before running or testing the code.
- Install new dependencies using `uv add <package-name>` to ensure they are added to the `pyproject.toml` file automatically.
- When there are changes to pydantic models update the frontend models using `frontend/scripts/generate-types.cjs`
- Use type hints for all functions and methods to ensure type safety and improve code readability.
- Create tests in the `backend/[directory]/tests/` directory and follow the testing guidelines provided in `backend-python-testing.instructions.md`.
- All interfaces should be defined using pydantic models for validation and type safety.
