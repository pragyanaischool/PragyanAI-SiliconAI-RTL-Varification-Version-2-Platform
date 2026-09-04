from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from core.llm import invoke_json
from config.settings import MAX_TEST_SCENARIOS

class VerificationPlannerAgent(BaseAgent):
    name = "Planning"
    step = 2

    def run(self, state: VerificationState):
        analysis = state.get("rtl_analysis", {})
        fallback = {
            "objectives": [
                {"id": "VP-001", "name": "Reset behavior", "priority": "critical"},
                {"id": "VP-002", "name": "Normal operation", "priority": "high"},
                {"id": "VP-003", "name": "Boundary conditions", "priority": "high"},
                {"id": "VP-004", "name": "Adversarial inputs", "priority": "medium"},
            ][:MAX_TEST_SCENARIOS],
            "target_coverage": 95,
        }
        result = invoke_json(
            "You are a senior RTL verification planner.",
            f"RTL analysis:\n{analysis}\nSpecification:\n{state.get('specification','')}",
            fallback,
        )
        return {"verification_plan": result}
