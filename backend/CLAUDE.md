# Backend Python Guidelines

## Development Instructions

- Always use the existing virtual environment: `source .venv/bin/activate`
- Install new dependencies using `uv add <package-name>` (adds to `pyproject.toml` automatically)
- When there are changes to pydantic models, update frontend models using `frontend/scripts/generate-types.cjs`
- Use type hints for all functions and methods
- All interfaces should be defined using pydantic models for validation and type safety

## Testing Guidelines

- **pytest** with `pytest-asyncio` for async test support
- **httpx** with `ASGITransport` for async API endpoint testing
- **unittest.mock** for mocking dependencies (AsyncMock, MagicMock, patch)
- Focus on testing high-value logic and critical paths; 100% coverage is not required

### Test Configuration

Test settings are defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --strict-markers --cov=src --cov-report=term-missing"
```

### Test File Organization

- Place all tests in `backend/tests/`
- Name test files with `test_` prefix (e.g., `test_server.py`)
- Group related tests in classes prefixed with `Test`
- Use descriptive test function names: `test_<action>_<expected_outcome>`

### Running Tests

```bash
source .venv/bin/activate
pytest                                    # All tests with coverage
pytest tests/test_server.py               # Specific file
pytest tests/test_server.py::TestClass    # Specific class
pytest -k "experiment"                    # Pattern match
```

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
@pytest.mark.asyncio
async def test_create_and_execute(self, orchestrator, db):
    """Test creating and executing a run."""
    # Arrange - Set up test data
    config = ExperimentConfigCreate(name="Test", prompt="Test prompt")
    experiment = await orchestrator.create_experiment(config)

    # Act - Perform the action being tested
    run = await orchestrator.create_run(experiment_id=experiment.id)

    # Assert - Verify the results
    assert run.id is not None
    assert run.status == "pending"
```

### TDD Workflow

1. Write a failing test that describes the expected behavior
2. Run the test to confirm it fails
3. Implement the minimum code to make the test pass
4. Run the test to confirm it passes
5. Refactor while keeping tests green
6. Add more tests for edge cases and error handling

### Best Practices

- Include a docstring describing what each test verifies
- Each test should be independent and not rely on other tests
- Add type hints to fixtures and test functions
- Test boundary conditions, error cases, and empty inputs
- Use fixtures with proper teardown to clean up test resources
