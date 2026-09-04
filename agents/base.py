"""Base Agent class providing shared execution hooks and CoT logging."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger("PragyanAI.Agents.Base")


class BaseAgent(ABC):
    def __init__(self, name: str, step_index: int):
        self.name = name
        self.step_index = step_index

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")
        iteration = state.get("iteration", 1)
        
        if run_logger:
            run_logger.started(self.name, self.step_index, iteration)

        start_time = time.time()
        try:
            result_state = self.process(state)
            duration_ms = (time.time() - start_time) * 1000.0
            
            if run_logger:
                run_logger.completed(self.name, self.step_index, iteration, duration_ms)
            return result_state

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            if run_logger:
                run_logger.failed(self.name, self.step_index, iteration, e)
            
            state.setdefault("errors", []).append(f"{self.name} failed: {str(e)}")
            return state

    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Implement agent-specific logic and LLM interaction here."""
        pass
        
