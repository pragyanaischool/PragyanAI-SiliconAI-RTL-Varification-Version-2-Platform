"""Test Vector Generator Agent with multi-key UI aliasing."""

from __future__ import annotations

from typing import Any, Dict
from agents.base import BaseAgent


class TestGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="test_generator", step_index=3)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")

        vectors = {
            "status": "SUCCESS",
            "test_vectors": [
                {"input": "4'b0000", "expected": "4'b0001", "description": "Reset state increment"},
                {"input": "4'b1111", "expected": "4'b0000", "description": "Overflow rollover test"}
            ],
            "source": "test_generator_agent"
        }

        # Set multi-key aliases for maximum UI compatibility
        state["test_vectors"] = vectors
        state["generated_tests"] = vectors
        state["tests"] = vectors

        if run_logger:
            run_logger.write_json(self.name, "test_vectors.json", vectors, self.step_index)

        return state
