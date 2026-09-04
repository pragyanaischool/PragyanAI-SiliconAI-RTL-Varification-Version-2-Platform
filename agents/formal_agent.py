from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState

class FormalAgent(BaseAgent):
    name = "Formal"
    step = 10

    def run(self, state: VerificationState):
        # Deliberately no SymbiYosys dependency.
        if not state.get("run_formal", False):
            return {"formal_result": {"status": "SKIPPED", "reason": "Formal verification disabled."}}
        return {"formal_result": {
            "status": "SKIPPED",
            "reason": "No formal backend configured. SymbiYosys is not required.",
        }}
