"""SSE streaming load test user — exercises /chat/stream endpoint.

Uses HttpUser (not FastHttpUser) because geventhttpclient does not
reliably support streaming iteration.
"""

from locust import HttpUser, between, tag, task

from loadtests.config import CRUD_TIMEOUT_S, MOCK_LLM
from loadtests.helpers.data_factory import (
    make_chat_request,
    make_create_thread_payload,
    make_thread_id,
)
from loadtests.helpers.sse_client import consume_sse_stream


class StreamUser(HttpUser):
    weight = 1
    wait_time = between(3, 10)

    def on_start(self):
        self.thread_id = make_thread_id()
        payload = make_create_thread_payload(self.thread_id)
        with self.client.post(
            "/threads",
            json=payload,
            catch_response=True,
            timeout=CRUD_TIMEOUT_S,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"setup: {resp.status_code}")

    @tag("stream")
    @task
    def stream_chat(self):
        if MOCK_LLM:
            # In mock mode, just hit the health endpoint instead of LLM
            self.client.get("/health", name="/chat/stream [MOCK]")
            return

        payload = make_chat_request(self.thread_id)
        consume_sse_stream(self.client, payload)

    def on_stop(self):
        if self.thread_id.startswith("lt-"):
            self.client.delete(
                f"/threads/{self.thread_id}",
                timeout=CRUD_TIMEOUT_S,
                name="/threads/[id] [DELETE cleanup]",
            )
