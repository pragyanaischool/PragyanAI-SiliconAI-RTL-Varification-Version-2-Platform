from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from config.settings import COVERAGE_TARGET

class CoverageAgent(BaseAgent):
    name = "Coverage"
    step = 7

    def run(self, state: VerificationState):
        tests = state.get("generated_tests", [])
        executed = len(tests) if state.get("simulation_passed") else 0
        score = min(100.0, executed / max(1, len(tests)) * 100.0)
        return {"coverage": {
            "type": "scenario_proxy",
            "score": score,
            "target": COVERAGE_TARGET,
            "tests_total": len(tests),
            "tests_executed": executed,
            "native_eda_coverage": False,
            "note": "This proxy does not claim commercial line/branch/toggle coverage.",
        }}
