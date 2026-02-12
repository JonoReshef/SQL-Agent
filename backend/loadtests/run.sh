#!/usr/bin/env bash
# Load testing convenience script for WestBrand backend.
# Run from the backend/ directory with the venv activated.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
HOST="${LOADTEST_BASE_URL:-http://localhost:8000}"

mkdir -p "$RESULTS_DIR"
cd "$BACKEND_DIR"

MODE="${1:-mock}"

case "$MODE" in
  mock)
    echo "=== Mode: Mock LLM (CRUD/DB throughput test) ==="
    LOADTEST_MOCK_LLM=true PYTHONPATH=. locust \
      -f "${SCRIPT_DIR}/locustfile.py" \
      --host "$HOST" \
      --headless \
      -u 100 -r 10 -t 3m \
      --csv="${RESULTS_DIR}/crud" \
      --html="${RESULTS_DIR}/crud.html"

    echo "Generating report..."
    PYTHONPATH=. python -m loadtests.report.generate_report \
      "${RESULTS_DIR}/crud" \
      "${RESULTS_DIR}/CRUD_REPORT.md"
    echo "Report: ${RESULTS_DIR}/CRUD_REPORT.md"
    ;;

  full)
    echo "=== Mode: Full (end-to-end with real LLM — costs money) ==="
    PYTHONPATH=. locust \
      -f "${SCRIPT_DIR}/locustfile.py" \
      --host "$HOST" \
      --headless \
      -u 60 -r 5 -t 5m \
      --csv="${RESULTS_DIR}/full" \
      --html="${RESULTS_DIR}/full.html"

    echo "Generating report..."
    PYTHONPATH=. python -m loadtests.report.generate_report \
      "${RESULTS_DIR}/full" \
      "${RESULTS_DIR}/FULL_REPORT.md"
    echo "Report: ${RESULTS_DIR}/FULL_REPORT.md"
    ;;

  staged)
    echo "=== Mode: Staged ramp (13-min shape test) ==="
    # Uncomment StagedShape import in locustfile.py before running
    PYTHONPATH=. locust \
      -f "${SCRIPT_DIR}/locustfile.py" \
      --host "$HOST" \
      --headless \
      --csv="${RESULTS_DIR}/staged" \
      --html="${RESULTS_DIR}/staged.html"

    echo "Generating report..."
    PYTHONPATH=. python -m loadtests.report.generate_report \
      "${RESULTS_DIR}/staged" \
      "${RESULTS_DIR}/STAGED_REPORT.md"
    echo "Report: ${RESULTS_DIR}/STAGED_REPORT.md"
    ;;

  *)
    echo "Usage: $0 {mock|full|staged}"
    echo "  mock   — CRUD-only with mock LLM (default, no cost)"
    echo "  full   — End-to-end with real LLM (costs money)"
    echo "  staged — 13-min staged ramp shape test"
    exit 1
    ;;
esac
