from __future__ import annotations
import re
from .base import BaseAgent
from core.state import VerificationState
from eda.iverilog_runner import IcarusRunner
from config.settings import MUTATION_TARGET

class MutationAgent(BaseAgent):
    name = "Mutation"
    step = 9

    def run(self, state: VerificationState):
        rtl = state.get("current_rtl") or ""
        tb = state.get("testbench") or ""
        mutations = []
        candidates = [
            (r"==", "!="),
            (r"!=", "=="),
            (r"<=", "<"),
            (r">=", ">"),
        ]
        for i, (old, new) in enumerate(candidates, 1):
            if re.search(old, rtl):
                mutated = re.sub(old, new, rtl, count=1)
                result = IcarusRunner().run(mutated, tb)
                killed = not result.get("simulation_passed", False)
                mutations.append({
                    "mutation_id": f"MUT-{i:03d}",
                    "operator": f"{old}_TO_{new}",
                    "killed": killed,
                    "mutated_rtl": mutated,
                    "simulation_result": result,
                })
        valid = len(mutations)
        killed = sum(1 for m in mutations if m["killed"])
        score = (killed / valid * 100.0) if valid else 100.0
        return {"mutation_results": mutations, "mutation_score": score,
                "mutation_target": MUTATION_TARGET}
