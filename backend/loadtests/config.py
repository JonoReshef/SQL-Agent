"""Load test configuration — all settings driven by environment variables."""

import os

BASE_URL = os.getenv("LOADTEST_BASE_URL", "http://localhost:8000")
MOCK_LLM = os.getenv("LOADTEST_MOCK_LLM", "false").lower() in ("true", "1", "yes")
STREAM_TIMEOUT_S = int(os.getenv("LOADTEST_STREAM_TIMEOUT_S", "120"))
CRUD_TIMEOUT_S = int(os.getenv("LOADTEST_CRUD_TIMEOUT_S", "10"))
