"""Automated Testbench Generator Agent with multi-key UI aliasing."""

from __future__ import annotations

from typing import Any, Dict
from agents.base import BaseAgent


class TestbenchGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="testbench_generator", step_index=4)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")
        
        generated_testbench = """
        module tb_auto_generated;
            reg clk;
            reg rst_n;
            wire [3:0] q;

            // Unit Under Test instantiation
            counter_4bit uut (
                .clk(clk),
                .rst_n(rst_n),
                .q(q)
            );

            initial begin
                $dumpfile("simulation.vcd");
                $dumpvars(0, tb_auto_generated);
                clk = 0;
                rst_n = 0;
                #15 rst_n = 1;
                #200 $finish;
            end

            always #5 clk = ~clk;
        endmodule
        """

        # Set multi-key aliases
        state["testbench_code"] = generated_testbench
        state["testbench"] = generated_testbench
        state["generated_testbench"] = generated_testbench

        if run_logger:
            run_logger.write_code(self.name, "testbench.v", generated_testbench, self.step_index)

        return state
