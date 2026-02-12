"""Custom Locust event hooks for SSE streaming metrics.

Metrics are fired from sse_client.py using the standard Locust events.request
mechanism with request_type="SSE". No additional setup is needed — Locust
aggregates them automatically into its stats tables.
"""
