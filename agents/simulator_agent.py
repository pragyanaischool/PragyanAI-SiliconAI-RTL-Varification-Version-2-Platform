from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from eda.iverilog_runner import IcarusRunner

class SimulatorAgent(BaseAgent):
    name = "Simulation"
    step = 5

    def run(self, state: VerificationState):
        result = IcarusRunner().run(
            state.get("current_rtl") or state.get("rtl_code") or "",
            state.get("testbench") or "",
        )
        return {
            "compile_passed": result["compile_passed"],
            "simulation_passed": result["simulation_passed"],
            "compile_output": result.get("compile_output", ""),
            "simulation_output": result.get("simulation_output", ""),
            "simulation_result": result,
        }
