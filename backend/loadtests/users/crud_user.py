"""CRUD-focused load test user — exercises thread and message endpoints."""

from locust import FastHttpUser, between, tag, task

from loadtests.config import CRUD_TIMEOUT_S
from loadtests.helpers.data_factory import (
    make_create_thread_payload,
    make_save_message_payload,
    make_thread_id,
    make_update_thread_payload,
)


class CrudUser(FastHttpUser):
    weight = 3
    wait_time = between(0.5, 2)

    def on_start(self):
        self.thread_ids: list[str] = []
        # Create an initial thread to operate on
        tid = make_thread_id()
        payload = make_create_thread_payload(tid)
        with self.client.post(
            "/threads",
            json=payload,
            catch_response=True,
            timeout=CRUD_TIMEOUT_S,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
                self.thread_ids.append(tid)
            else:
                resp.failure(f"setup: {resp.status_code}")

    @tag("read")
    @task(5)
    def list_threads(self):
        self.client.get("/threads", timeout=CRUD_TIMEOUT_S)

    @tag("read")
    @task(3)
    def list_messages(self):
        if not self.thread_ids:
            return
        tid = self.thread_ids[0]
        self.client.get(
            f"/threads/{tid}/messages",
            timeout=CRUD_TIMEOUT_S,
            name="/threads/[id]/messages",
        )

    @tag("write")
    @task(2)
    def create_thread(self):
        tid = make_thread_id()
        payload = make_create_thread_payload(tid)
        with self.client.post(
            "/threads",
            json=payload,
            catch_response=True,
            timeout=CRUD_TIMEOUT_S,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
                self.thread_ids.append(tid)
            else:
                resp.failure(f"{resp.status_code}")

    @tag("write")
    @task(3)
    def save_message(self):
        if not self.thread_ids:
            return
        tid = self.thread_ids[0]
        payload = make_save_message_payload(tid)
        self.client.post(
            f"/threads/{tid}/messages",
            json=payload,
            timeout=CRUD_TIMEOUT_S,
            name="/threads/[id]/messages [POST]",
        )

    @tag("write")
    @task(1)
    def update_thread(self):
        if not self.thread_ids:
            return
        tid = self.thread_ids[0]
        payload = make_update_thread_payload()
        self.client.patch(
            f"/threads/{tid}",
            json=payload,
            timeout=CRUD_TIMEOUT_S,
            name="/threads/[id] [PATCH]",
        )

    @tag("write")
    @task(1)
    def delete_thread(self):
        if len(self.thread_ids) <= 1:
            return  # Keep at least one thread
        tid = self.thread_ids.pop()
        self.client.delete(
            f"/threads/{tid}",
            timeout=CRUD_TIMEOUT_S,
            name="/threads/[id] [DELETE]",
        )

    def on_stop(self):
        for tid in self.thread_ids:
            if tid.startswith("lt-"):
                self.client.delete(
                    f"/threads/{tid}",
                    timeout=CRUD_TIMEOUT_S,
                    name="/threads/[id] [DELETE cleanup]",
                )
