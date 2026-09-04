"""Simulator Agent for executing RTL and testbench compilations and simulations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from agents.base import BaseAgent
from eda.iverilog_runner import run_iverilog_simulation


class SimulatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="simulator_agent", step_index=5)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")
        
        # Determine project name or explicit file paths
        project_name = state.get("project_name", "counter_4bit")
        
        # Default fallback paths to sample projects
        default_rtl = f"examples/sample_projects/{project_name}/rtl.v"
        default_tb = f"examples/sample_projects/{project_name}/testbench.v"

        rtl_path = state.get("rtl_file_path") or default_rtl
        tb_path = state.get("testbench_file_path") or default_tb

        # If a testbench was dynamically generated in previous steps, write/use it from the run directory
        if run_logger and "testbench_code" in state:
            tb_dir = run_logger.run_dir / "04_testbench_generation"
            tb_dir.mkdir(parents=True, exist_ok=True)
            dynamic_tb_path = tb_dir / "testbench.v"
            dynamic_tb_path.write_text(state["testbench_code"], encoding="utf-8")
            tb_path = dynamic_tb_path

        # If RTL code was dynamically passed in state, write it out
        if run_logger and "rtl_code" in state and state["rtl_code"]:
            rtl_dir = run_logger.run_dir / "01_rtl_analysis"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            dynamic_rtl_path = rtl_dir / "rtl.v"
            dynamic_rtl_path.write_text(state["rtl_code"], encoding="utf-8")
            rtl_path = dynamic_rtl_path

        # Execute simulation via Icarus Verilog wrapper
        executable_out = run_logger.run_dir / "simulation_executable" if run_logger else "runtime/runs/sim_out"
        sim_results = run_iverilog_simulation(
            rtl_path=rtl_path,
            tb_path=tb_path,
            output_executable=executable_out
        )

        state["simulation_results"] = sim_results
        
        if run_logger:
            run_logger.write_json(
                self.name, 
                "simulation_results.json", 
                sim_results, 
                self.step_index
            )

        return state
