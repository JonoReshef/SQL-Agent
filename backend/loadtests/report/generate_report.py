"""Parse Locust CSV output and generate a Markdown report."""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def generate(csv_prefix: str, output_path: str) -> None:
    """
    Generate a Markdown report from Locust CSV files.

    Args:
        csv_prefix: Path prefix for Locust CSVs (e.g. "results/crud")
                    Expects files: {prefix}_stats.csv, {prefix}_stats_history.csv,
                    {prefix}_failures.csv
        output_path: Where to write the Markdown report
    """
    prefix = Path(csv_prefix)
    stats_rows = _read_csv(Path(f"{prefix}_stats.csv"))
    history_rows = _read_csv(Path(f"{prefix}_stats_history.csv"))
    failure_rows = _read_csv(Path(f"{prefix}_failures.csv"))

    # --- Per-endpoint stats ---
    endpoints = []
    aggregated = None
    for row in stats_rows:
        name = row.get("Name", "")
        entry = {
            "name": name,
            "requests": _safe_int(row.get("Request Count", "0")),
            "failures": _safe_int(row.get("Failure Count", "0")),
            "median": round(_safe_float(row.get("Median Response Time", "0")), 1),
            "p95": round(_safe_float(row.get("95%", "0")), 1),
            "p99": round(_safe_float(row.get("99%", "0")), 1),
            "max": round(_safe_float(row.get("Max Response Time", "0")), 1),
        }
        if name == "Aggregated":
            aggregated = entry
        else:
            endpoints.append(entry)

    # --- Streaming metrics (from SSE custom entries) ---
    streaming_metrics = None
    ttft_row = next(
        (r for r in stats_rows if r.get("Name") == "TTFT"), None
    )
    tps_row = next(
        (r for r in stats_rows if r.get("Name") == "tokens/sec"), None
    )
    if ttft_row:
        streaming_metrics = {
            "avg_ttft_ms": round(_safe_float(ttft_row.get("Average Response Time", "0")), 1),
            "p95_ttft_ms": round(_safe_float(ttft_row.get("95%", "0")), 1),
            "avg_tps": round(
                _safe_float(tps_row.get("Average Response Time", "0")), 1
            )
            if tps_row
            else "N/A",
            "completion_rate": round(
                (
                    1
                    - _safe_int(ttft_row.get("Failure Count", "0"))
                    / max(_safe_int(ttft_row.get("Request Count", "1")), 1)
                )
                * 100,
                1,
            ),
        }

    # --- Service limits from time-series data ---
    max_rps = 0.0
    peak_users = 0
    max_users_before_errors = 0
    first_error_seen = False

    for row in history_rows:
        rps = _safe_float(row.get("Requests/s", "0"))
        users = _safe_int(row.get("User Count", row.get("User count", "0")))
        fails = _safe_float(row.get("Failures/s", "0"))

        if rps > max_rps:
            max_rps = rps
        if users > peak_users:
            peak_users = users
        if not first_error_seen and fails < 0.01:
            max_users_before_errors = users
        elif fails >= 0.01:
            first_error_seen = True

    if not first_error_seen:
        max_users_before_errors = peak_users

    # Stable-load percentiles (use aggregated row from stats CSV)
    agg_stats = next(
        (r for r in stats_rows if r.get("Name") == "Aggregated"), None
    )
    p95_stable = _safe_float(agg_stats.get("95%", "0")) if agg_stats else 0
    p99_stable = _safe_float(agg_stats.get("99%", "0")) if agg_stats else 0

    limits = {
        "max_rps": round(max_rps, 1),
        "max_users_before_errors": max_users_before_errors,
        "p95_stable_ms": round(p95_stable, 1),
        "p99_stable_ms": round(p99_stable, 1),
        "threadpool_saturation": "N/A (mock mode)" if not streaming_metrics else "See streaming metrics",
        "db_error_threshold": max_users_before_errors if first_error_seen else "Not reached",
    }

    # --- Duration ---
    duration_s = 0
    if history_rows:
        timestamps = [
            _safe_float(r.get("Timestamp", "0")) for r in history_rows
        ]
        if timestamps:
            duration_s = round(max(timestamps) - min(timestamps))

    # --- Errors ---
    errors = []
    for row in failure_rows:
        errors.append(
            {
                "type": row.get("Name", "unknown"),
                "count": _safe_int(row.get("Occurrences", row.get("Error Count", "0"))),
                "first_seen_users": "N/A",
            }
        )

    # --- Summary ---
    total_requests = aggregated["requests"] if aggregated else 0
    total_failures = aggregated["failures"] if aggregated else 0
    fail_rate = (
        round(total_failures / max(total_requests, 1) * 100, 2)
    )
    summary = (
        f"Tested with up to **{peak_users} concurrent users** over **{duration_s}s**. "
        f"Processed **{total_requests:,} requests** with a **{fail_rate}% failure rate**. "
        f"Peak throughput: **{limits['max_rps']} req/s**."
    )

    # --- Bottleneck analysis ---
    bottleneck_db = (
        "NullPool creates a new DB connection per request. Under high concurrency "
        "this can exhaust PostgreSQL's `max_connections` (default 100). "
        f"{'Errors observed — likely connection exhaustion.' if first_error_seen else 'No connection errors observed at tested load levels.'}"
    )
    bottleneck_threadpool = (
        "The `ThreadPoolExecutor(max_workers=10)` limits concurrent stream workers. "
        "Requests beyond 10 concurrent streams queue until a worker is free. "
        "Consider increasing `max_workers` or switching to async streaming."
    )
    bottleneck_external = (
        "Azure OpenAI latency dominates stream response times. "
        "TTFT and total stream duration are bounded by LLM inference speed."
        if streaming_metrics
        else "External LLM was not tested (mock mode)."
    )

    # --- Recommendations ---
    recommendations = [
        "Replace `NullPool` with `QueuePool` (pool_size=20, max_overflow=10) for connection reuse",
        "Increase `ThreadPoolExecutor.max_workers` from 10 to 20-30 to handle more concurrent streams",
        "Consider migrating `_stream_worker` to async (asyncio + async SQLAlchemy) to eliminate the thread pool bottleneck",
        "Add connection health checks and retry logic for DB connections under load",
        "Implement rate limiting on `/chat/stream` to prevent LLM cost overruns",
    ]

    # --- Render ---
    template_path = Path(__file__).parent / "template.md"
    template = Template(template_path.read_text())
    report = template.render(
        generated_at=datetime.now(timezone.utc).isoformat(),
        duration_s=duration_s,
        peak_users=peak_users,
        summary=summary,
        limits=limits,
        endpoints=endpoints,
        streaming_metrics=streaming_metrics,
        errors=errors,
        bottleneck_db=bottleneck_db,
        bottleneck_threadpool=bottleneck_threadpool,
        bottleneck_external=bottleneck_external,
        recommendations=recommendations,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report)
    print(f"Report written to {output}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m loadtests.report.generate_report <csv_prefix> <output.md>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
