"""SSE stream consumer for Locust — reports the full stream as one request entry."""

import json
import time

from locust import events

from loadtests.config import STREAM_TIMEOUT_S


def consume_sse_stream(client, payload: dict) -> dict:
    """
    POST to /chat/stream, iterate SSE lines, and report as a single Locust request.

    Returns a dict with stream metrics:
        tokens, ttft_ms, duration_ms, success, error
    """
    start = time.perf_counter()
    first_token_time = None
    tokens = 0
    error_msg = None
    success = True

    try:
        with client.post(
            "/chat/stream",
            json=payload,
            stream=True,
            catch_response=True,
            timeout=STREAM_TIMEOUT_S,
            name="/chat/stream [SSE]",
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return {
                    "tokens": 0,
                    "ttft_ms": 0,
                    "duration_ms": 0,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }

            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                if not decoded.startswith("data: "):
                    continue

                try:
                    data = json.loads(decoded[6:])
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type", "")

                if event_type == "token":
                    tokens += 1
                    if first_token_time is None:
                        first_token_time = time.perf_counter()

                elif event_type == "error":
                    error_msg = data.get("content", "unknown error")
                    success = False

                elif event_type == "end":
                    break

            elapsed_ms = (time.perf_counter() - start) * 1000

            if success:
                response.success()
            else:
                response.failure(error_msg)

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        error_msg = str(exc)
        success = False

    ttft_ms = (
        (first_token_time - start) * 1000 if first_token_time is not None else 0
    )

    # Fire custom metrics
    if first_token_time is not None:
        events.request.fire(
            request_type="SSE",
            name="TTFT",
            response_time=ttft_ms,
            response_length=0,
            exception=None,
            context={},
        )

    if tokens > 0 and elapsed_ms > 0:
        tps = tokens / (elapsed_ms / 1000)
        events.request.fire(
            request_type="SSE",
            name="tokens/sec",
            response_time=tps,
            response_length=tokens,
            exception=None,
            context={},
        )

    return {
        "tokens": tokens,
        "ttft_ms": round(ttft_ms, 1),
        "duration_ms": round(elapsed_ms, 1),
        "success": success,
        "error": error_msg,
    }
