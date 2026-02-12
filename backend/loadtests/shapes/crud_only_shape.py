"""Aggressive 5.5-minute ramp to isolate DB/NullPool limits (no LLM)."""

import math

from locust import LoadTestShape


class CrudOnlyShape(LoadTestShape):
    """
    Stages:
        0-30s    : 0→20    warm-up
        30-90s   : 20→100  ramp
        90-150s  : 100→250 heavy ramp
        150-210s : 250→500 overload ramp
        210-300s : 500     hold at peak
        300-330s : 500→0   cool-down
    """

    stages = [
        (30, 0, 20, 5),
        (90, 20, 100, 5),
        (150, 100, 250, 10),
        (210, 250, 500, 15),
        (300, 500, 500, 15),
        (330, 500, 0, 20),
    ]

    def tick(self):
        run_time = self.get_run_time()
        prev_end = 0

        for end_time, start_users, end_users, spawn_rate in self.stages:
            if run_time <= end_time:
                stage_elapsed = run_time - prev_end
                stage_duration = end_time - prev_end
                progress = stage_elapsed / stage_duration if stage_duration > 0 else 1
                user_count = math.ceil(
                    start_users + (end_users - start_users) * progress
                )
                user_count = max(user_count, 0)
                return user_count, spawn_rate
            prev_end = end_time

        return None
