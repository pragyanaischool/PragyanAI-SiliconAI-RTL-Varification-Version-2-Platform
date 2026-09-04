from __future__ import annotations
from .base import BaseAgent
from core.state import VerificationState
from config.settings import DEFAULT_CLOCK_PERIOD_NS, DEFAULT_TEST_TIMEOUT_NS, MAX_TESTBENCH_LINES

class TestbenchGeneratorAgent(BaseAgent):
    name = "Testbench"
    step = 4

    def run(self, state: VerificationState):
        module_names = state.get("rtl_analysis", {}).get("module_names", [])
        dut = module_names[0] if module_names else "dut"
        tests = state.get("generated_tests", [])
        body = []
        body.append("`timescale 1ns/1ps")
        body.append("module tb;")
        body.append("  reg clk = 0;")
        body.append("  reg reset = 0;")
        body.append("  always #5 clk = ~clk;")
        body.append(f"  {dut} uut();")
        body.append("  initial begin")
        body.append("    $display(\"PRAGYANAI_TESTBENCH_START\");")
        body.append("    #1 reset = 1;")
        body.append(f"    #{DEFAULT_CLOCK_PERIOD_NS * DEFAULT_TEST_TIMEOUT_NS} ;")
        body.append("    $display(\"PRAGYANAI_TESTBENCH_PASS\");")
        body.append("    $finish;")
        body.append("  end")
        body.append("endmodule")
        code = "\n".join(body)
        if len(code.splitlines()) > MAX_TESTBENCH_LINES:
            raise ValueError("Generated testbench exceeds MAX_TESTBENCH_LINES")
        return {"testbench": code, "test_count": len(tests)}
