"""13-minute staged ramp to find breaking points."""

import math

from locust import LoadTestShape


class StagedShape(LoadTestShape):
    """
    Stages:
        0-60s    : 0→10   warm-up
        60-180s  : 10     baseline
        180-240s : 10→30  moderate ramp
        240-360s : 30     moderate hold
        360-420s : 30→60  heavy ramp
        420-540s : 60     heavy hold
        540-600s : 60→100 overload ramp
        600-720s : 100    overload hold
        720-780s : 100→0  cool-down
    """

    stages = [
        # (end_time, start_users, end_users, spawn_rate)
        (60, 0, 10, 1),
        (180, 10, 10, 1),
        (240, 10, 30, 1),
        (360, 30, 30, 1),
        (420, 30, 60, 1),
        (540, 60, 60, 1),
        (600, 60, 100, 2),
        (720, 100, 100, 2),
        (780, 100, 0, 5),
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

        return None  # Test complete
