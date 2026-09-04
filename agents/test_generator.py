from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from config.settings import MAX_TEST_CASES

class TestGeneratorAgent(BaseAgent):
    name = "Test Generation"
    step = 3

    def run(self, state: VerificationState):
        objectives = state.get("verification_plan", {}).get("objectives", [])
        tests = []
        for i, obj in enumerate(objectives[:MAX_TEST_CASES], 1):
            tests.append({
                "id": f"TEST-{i:03d}",
                "scenario_id": obj.get("id", f"VP-{i:03d}"),
                "name": obj.get("name", f"Scenario {i}"),
                "priority": obj.get("priority", "medium"),
                "stimulus": f"Exercise {obj.get('name','verification objective')}",
                "expected": "No unexpected DUT behavior; required checks pass.",
            })
        return {"generated_tests": tests}
