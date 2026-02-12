# WestBrand Load Test Report

**Generated**: {{ generated_at }}
**Test Duration**: {{ duration_s }}s
**Peak Users**: {{ peak_users }}

---

## Executive Summary

{{ summary }}

---

## Service Limits

| Metric | Value |
|--------|-------|
| Max Sustained Throughput (req/s) | {{ limits.max_rps }} |
| Max Users Before Errors | {{ limits.max_users_before_errors }} |
| p95 Latency at Stable Load | {{ limits.p95_stable_ms }}ms |
| p99 Latency at Stable Load | {{ limits.p99_stable_ms }}ms |
| ThreadPool Saturation Point | {{ limits.threadpool_saturation }} users |
| DB Error Threshold | {{ limits.db_error_threshold }} users |

---

## Per-Endpoint Performance

| Endpoint | Requests | Failures | Median (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|----------|----------|----------|-------------|----------|----------|----------|
{% for ep in endpoints -%}
| {{ ep.name }} | {{ ep.requests }} | {{ ep.failures }} | {{ ep.median }} | {{ ep.p95 }} | {{ ep.p99 }} | {{ ep.max }} |
{% endfor %}

---

{% if streaming_metrics %}
## Streaming Metrics

| Metric | Value |
|--------|-------|
| Avg TTFT | {{ streaming_metrics.avg_ttft_ms }}ms |
| p95 TTFT | {{ streaming_metrics.p95_ttft_ms }}ms |
| Avg Tokens/sec | {{ streaming_metrics.avg_tps }} |
| Stream Completion Rate | {{ streaming_metrics.completion_rate }}% |

---
{% endif %}

## Error Analysis

{% if errors %}
| Error Type | Count | First Seen At (users) |
|------------|-------|-----------------------|
{% for err in errors -%}
| {{ err.type }} | {{ err.count }} | {{ err.first_seen_users }} |
{% endfor %}
{% else %}
No errors recorded.
{% endif %}

---

## Bottleneck Analysis

### DB Connection Pool (NullPool)
{{ bottleneck_db }}

### ThreadPoolExecutor (max_workers=10)
{{ bottleneck_threadpool }}

### External Dependencies (Azure OpenAI)
{{ bottleneck_external }}

---

## Recommendations

{% for rec in recommendations -%}
- {{ rec }}
{% endfor %}
