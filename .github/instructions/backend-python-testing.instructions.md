---
description: Python backend testing guidelines
applyTo: 'backend/tests/**/*.py'
---

# Backend Python Testing Guidelines

See also: `backend/tests/README.md` for a summary of all test files and their purposes.

## Goal of Testing

- Ensure backend services and utilities work as expected
- Catch regressions early during development
- Facilitate safe refactoring and feature additions
- Focus on testing high value logic and critical paths, 100% coverage is not required

## Test Framework

- **pytest** with `pytest-asyncio` for async test support
- **httpx** with `ASGITransport` for async API endpoint testing
- **FastAPI TestClient** for synchronous API tests
- **unittest.mock** for mocking dependencies (AsyncMock, MagicMock, patch)

## Test Configuration

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

## Test File Organization

- Place all tests in `backend/tests/`
- Name test files with `test_` prefix (e.g., `test_experiment_service.py`)
- Group related tests in classes prefixed with `Test` (e.g., `TestExperimentOrchestrator`)
- Use descriptive test function names: `test_<action>_<expected_outcome>`

### Current Test Files

| File                   | Purpose                                                       |
| ---------------------- | ------------------------------------------------------------- |
| `conftest.py`          | Shared fixtures (event_loop, async clients, database session) |
| `test_adapters.py`     | Data adapters (PDF, CSV, JSON, image, text)                   |
| `test_database.py`     | Database connection and async sessions                        |
| `test_documents.py`    | Document CRUD and API endpoints                               |
| `test_experiment_*.py` | Experiment service, schemas, filtering, history               |
| `test_server.py`       | FastAPI route and endpoint tests                              |
| `test_tools.py`        | LangChain tools (calculator, data analyzer, etc.)             |
| `test_workflow.py`     | LangGraph workflow execution and state                        |

## Running Tests

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_server.py

# Run specific test class
pytest tests/test_experiment_service.py::TestExperimentOrchestrator

# Run specific test
pytest tests/test_server.py::test_health_check

# Run tests matching a pattern
pytest -k "experiment"

# Run with verbose output
pytest -v

# Run without coverage
pytest --no-cov
```

## Fixtures

### Shared Fixtures (conftest.py)

The `conftest.py` file provides these shared fixtures:

```python
import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    from src.server.server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db():
    """Create a test database session with fresh tables."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from src.database.models import Base

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()
```

### Test-Specific Fixtures

Define fixtures within test classes for specific setup:

```python
class TestExperimentOrchestrator:
    @pytest.fixture
    async def orchestrator(self, db: AsyncSession):
        """Create orchestrator instance for testing."""
        return ExperimentOrchestrator(db)
```

### Temporary File Fixtures

For tests that need temporary files:

```python
@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def text_file(test_data_dir: Path) -> Path:
    """Create a test text file."""
    text_path = test_data_dir / "test.txt"
    text_path.write_text("Test content")
    return text_path
```

## Writing Tests

### Synchronous Tests

Use `TestClient` for synchronous endpoint tests:

```python
from fastapi.testclient import TestClient
from src.server.server import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint returns success."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Async Tests

Mark async tests with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_create_experiment(self, orchestrator, db):
    """Test creating an experiment configuration."""
    config = ExperimentConfigCreate(
        name="Test Experiment",
        prompt="Analyze: {documents}",
        document_ids=[],
        configurations=[RunConfiguration(model_name="gpt-4o", tool_names=[])],
    )

    experiment = await orchestrator.create_experiment(config)

    assert experiment.id is not None
    assert experiment.name == "Test Experiment"
```

### Mocking

Use `unittest.mock` for mocking external dependencies:

```python
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_with_mock(self, orchestrator):
    """Test with mocked workflow."""
    with patch.object(
        orchestrator, 'workflow', new_callable=AsyncMock
    ) as mock_workflow:
        mock_workflow.run.return_value = {"result": "success"}

        result = await orchestrator.execute_run(run_id)

        mock_workflow.run.assert_called_once()
```

## Test Structure

Follow the Arrange-Act-Assert pattern:

```python
@pytest.mark.asyncio
async def test_create_and_execute_run(self, orchestrator, db):
    """Test creating and executing a run."""
    # Arrange - Set up test data
    config = ExperimentConfigCreate(
        name="Test",
        prompt="Test prompt",
        configurations=[RunConfiguration(model_name="gpt-4o", tool_names=[])],
    )
    experiment = await orchestrator.create_experiment(config)

    # Act - Perform the action being tested
    run = await orchestrator.create_run(
        experiment_id=experiment.id,
        model_name="gpt-4o",
        tool_names=[],
        configuration_index=0,
        run_number=1,
    )

    # Assert - Verify the results
    assert run.id is not None
    assert run.status == "pending"
```

## Best Practices

1. **Docstrings**: Include a docstring describing what each test verifies
2. **Isolation**: Each test should be independent and not rely on other tests
3. **Type hints**: Add type hints to fixtures and test functions
4. **Descriptive names**: Use clear, descriptive test names that explain the scenario
5. **Edge cases**: Test boundary conditions, error cases, and empty inputs
6. **Cleanup**: Use fixtures with proper teardown to clean up test resources

## TDD Workflow

1. Write a failing test that describes the expected behavior
2. Run the test to confirm it fails
3. Implement the minimum code to make the test pass
4. Run the test to confirm it passes
5. Refactor while keeping tests green
6. Add more tests for edge cases and error handling
