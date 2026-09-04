from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from config.settings import VERIFICATION_SCORE_TARGET

class VerificationJudgeAgent(BaseAgent):
    name = "Judge"
    step = 11

    def run(self, state: VerificationState):
        simulation = 100 if state.get("simulation_passed") else 0
        coverage = float(state.get("coverage", {}).get("score", 0))
        mutation = float(state.get("mutation_score", 100))
        formal = 100 if state.get("formal_result", {}).get("status") == "PASS" else 80
        score = 0.45 * simulation + 0.25 * coverage + 0.20 * mutation + 0.10 * formal
        verdict = "PASS" if score >= VERIFICATION_SCORE_TARGET else "NEED_MORE"
        return {"judge_result": {
            "verification_score": round(score, 2),
            "target": VERIFICATION_SCORE_TARGET,
            "verdict": verdict,
            "evidence": {
                "simulation": state.get("simulation_result", {}),
                "coverage": state.get("coverage", {}),
                "mutation_score": mutation,
                "formal": state.get("formal_result", {}),
            },
        }, "final_verdict": verdict,
           "verification_score": round(score, 2)}
