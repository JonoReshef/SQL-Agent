"""Realistic user session — list → create → stream → fetch → cleanup."""

from locust import HttpUser, between, tag, task

from loadtests.config import CRUD_TIMEOUT_S, MOCK_LLM
from loadtests.helpers.data_factory import (
    make_chat_request,
    make_create_thread_payload,
    make_thread_id,
)
from loadtests.helpers.sse_client import consume_sse_stream


class MixedUser(HttpUser):
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        self.thread_ids: list[str] = []

    @tag("mixed")
    @task
    def full_session(self):
        # 1. List threads
        self.client.get("/threads", timeout=CRUD_TIMEOUT_S)

        # 2. Create thread
        tid = make_thread_id()
        payload = make_create_thread_payload(tid)
        with self.client.post(
            "/threads",
            json=payload,
            catch_response=True,
            timeout=CRUD_TIMEOUT_S,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"create: {resp.status_code}")
                return
            resp.success()
            self.thread_ids.append(tid)

        # 3. Stream a chat (or mock)
        if not MOCK_LLM:
            chat_payload = make_chat_request(tid)
            consume_sse_stream(self.client, chat_payload)
        else:
            self.client.get("/health", name="/chat/stream [MOCK]")

        # 4. Fetch messages
        self.client.get(
            f"/threads/{tid}/messages",
            timeout=CRUD_TIMEOUT_S,
            name="/threads/[id]/messages",
        )

        # 5. List threads again
        self.client.get("/threads", timeout=CRUD_TIMEOUT_S)

    def on_stop(self):
        for tid in self.thread_ids:
            if tid.startswith("lt-"):
                self.client.delete(
                    f"/threads/{tid}",
                    timeout=CRUD_TIMEOUT_S,
                    name="/threads/[id] [DELETE cleanup]",
                )
