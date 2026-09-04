from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState

class FailureAnalyzerAgent(BaseAgent):
    name = "Failure Analysis"
    step = 6

    def run(self, state: VerificationState):
        compile_output = state.get("compile_output", "")
        simulation_output = state.get("simulation_output", "")
        if not state.get("compile_passed", False):
            failure_type = "COMPILATION_ERROR"
        elif not state.get("simulation_passed", False):
            failure_type = "SIMULATION_ERROR"
        else:
            failure_type = "NONE"
        return {"failure_analysis": {
            "failure_type": failure_type,
            "root_cause": (compile_output or simulation_output)[-3000:],
            "evidence": [compile_output[-1000:], simulation_output[-1000:]],
            "recommended_action": "REGENERATE_TESTS" if failure_type != "NONE" else "CONTINUE",
        }}
