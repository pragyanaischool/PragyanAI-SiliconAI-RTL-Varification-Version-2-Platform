"""Simulator Execution Agent wrapping Icarus Verilog."""

from __future__ import annotations

from typing import Any, Dict
from agents.base import BaseAgent
from eda.iverilog_runner import run_iverilog_simulation


class SimulatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="simulator_agent", step_index=5)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")
        
        rtl_path = state.get("rtl_file_path", "examples/sample_projects/counter_4bit/rtl.v")
        tb_path = state.get("testbench_file_path", "examples/sample_projects/counter_4bit/testbench.v")

        # If files were written dynamically during the run, resolve them from the run directory
        if run_logger:
            dynamic_tb = run_logger.run_dir / "04_testbench_generation" / "testbench.v"
            if dynamic_tb.exists():
                tb_path = dynamic_tb

        sim_results = run_iverilog_simulation(rtl_path=rtl_path, tb_path=tb_path)

        state["simulation_results"] = sim_results
        if run_logger:
            run_logger.write_json(self.name, "simulation_results.json", sim_results, self.step_index)

        return state
        
