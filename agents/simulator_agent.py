"""Simulator Agent with robust dynamic file writing and fallback handling."""

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
        run_dir = run_logger.run_dir if run_logger else Path("runtime/runs/default_run")
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Resolve or extract RTL code
        spec = state.get("specification", {})
        rtl_code = (
            state.get("rtl_code")
            or (spec.get("rtl_code") if isinstance(spec, dict) else None)
            or spec if isinstance(spec, str) and len(spec) > 10 else None
        )

        rtl_path = run_dir / "design.v"
        if rtl_code:
            rtl_path.write_text(str(rtl_code), encoding="utf-8")
        else:
            # Fallback to sample project if no custom RTL provided
            project_name = state.get("project_name", "counter_4bit")
            sample_rtl = Path(f"examples/sample_projects/{project_name}/rtl.v")
            if sample_rtl.exists():
                rtl_path = sample_rtl
            else:
                # Minimal valid fallback counter module
                fallback_rtl = """
                module counter_4bit (
                    input wire clk,
                    input wire rst_n,
                    output reg [3:0] q
                );
                    always @(posedge clk or negedge rst_n) begin
                        if (!rst_n) q <= 4'b0000;
                        else q <= q + 1;
                    end
                endmodule
                """
                rtl_path.write_text(fallback_rtl, encoding="utf-8")

        # 2. Resolve or extract Testbench code
        tb_code = state.get("testbench_code")
        tb_path = run_dir / "testbench.v"
        if tb_code:
            tb_path.write_text(str(tb_code), encoding="utf-8")
        else:
            # Fallback testbench
            fallback_tb = """
            module tb;
                reg clk = 0;
                reg rst_n = 0;
                wire [3:0] q;

                counter_4bit uut (.clk(clk), .rst_n(rst_n), .q(q));

                initial begin
                    $dumpfile("sim.vcd");
                    $dumpvars(0, tb);
                    #15 rst_n = 1;
                    #100 $finish;
                end

                always #5 clk = ~clk;
            endmodule
            """
            tb_path.write_text(fallback_tb, encoding="utf-8")

        # 3. Execute Simulation
        executable_out = run_dir / "sim_executable"
        sim_results = run_iverilog_simulation(
            rtl_path=rtl_path,
            tb_path=tb_path,
            output_executable=executable_out
        )

        state["simulation_results"] = sim_results
        state["rtl_file_path"] = str(rtl_path)
        state["testbench_file_path"] = str(tb_path)

        if run_logger:
            run_logger.write_json(
                self.name,
                "simulation_results.json",
                sim_results,
                self.step_index
            )

        return state
