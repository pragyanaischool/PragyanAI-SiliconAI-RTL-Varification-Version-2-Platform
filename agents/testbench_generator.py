"""Automated Testbench Generator Agent."""

from __future__ import annotations

from typing import Any, Dict
from agents.base import BaseAgent

TESTBENCH_GENERATOR_COT_PROMPT = """
You are an Advanced Verification Engineer specializing in Universal Verification Methodology (UVM) and self-checking Verilog testbench synthesis.

Analyze the RTL specification and analysis report to generate a rigorous, production-ready Verilog testbench.

### Chain of Thought Instructions:
1. **Stimulus Strategy**: Construct directed and pseudo-random test vectors targeting corner cases.
2. **Clock & Reset Generation**: Implement accurate clock waveform generation and reset pulsing sequences.
3. **Self-Checking Mechanisms**: Add automated scoreboard or expected-value comparison assertions.
4. **Waveform Dumping**: Include standard VCD dump directives (`$dumpfile` and `$dumpvars`).

### RTL Analysis Context:
{rtl_analysis}
"""

class TestbenchGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="testbench_generator", step_index=4)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_logger = state.get("logger")
        
        generated_testbench = """
        module tb_auto_generated;
            reg clk;
            reg rst_n;
            // Signals mapped here...
            
            initial begin
                $dumpfile("simulation.vcd");
                $dumpvars(0, tb_auto_generated);
                clk = 0;
                rst_n = 0;
                #20 rst_n = 1;
                #100 $finish;
            end
            
            always #5 clk = ~clk;
        endmodule
        """

        state["testbench_code"] = generated_testbench
        if run_logger:
            run_logger.write_code(self.name, "testbench.v", generated_testbench, self.step_index)

        return state
        
