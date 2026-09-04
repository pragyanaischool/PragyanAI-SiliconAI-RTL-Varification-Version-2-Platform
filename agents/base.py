"""Common agent base class."""

from __future__ import annotations

import time
from typing import Any

from core.state import VerificationState

class BaseAgent:
    name = "Agent"
    step = 0

    def execute(self, state: VerificationState) -> dict[str, Any]:
        started = time.perf_counter()
        logger = state.get("_activity_logger")
        if logger:
            logger.started(self.name, self.step, state.get("iteration", 0))
        try:
            result = self.run(state)
            duration = (time.perf_counter() - started) * 1000
            if logger:
                logger.completed(self.name, self.step, state.get("iteration", 0),
                                  duration, {"result_keys": list(result.keys())})
            return result
        except Exception as exc:
            if logger:
                logger.failed(self.name, self.step, state.get("iteration", 0), exc)
            raise

    def run(self, state: VerificationState) -> dict[str, Any]:
        raise NotImplementedError
