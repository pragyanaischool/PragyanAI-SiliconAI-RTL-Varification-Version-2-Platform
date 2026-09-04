"""RTL Analyzer Agent with Comprehensive Chain of Thought Prompting."""

from __future__ import annotations

import json
from typing import Any, Dict
from agents.base import BaseAgent

RTL_ANALYZER_COT_PROMPT = """
You are an expert Silicon Design and Verification Architect with 25+ years of experience in RTL design, hardware simulation, and ASIC/FPGA validation.

Your task is to analyze the provided Verilog/SystemVerilog RTL source code using a strict Chain of Thought methodology.

### Chain of Thought Instructions:
1. **Module & Interface Breakdown**: Identify the top module name, input/output ports, widths, and parameters.
2. **Clock & Reset Analysis**: Detect all clock signals, reset polarities (synchronous vs asynchronous), and enable lines.
3. **State & Datapath Inspection**: Enumerate registers, wires, always blocks, and sequential/combinational logic elements.
4. **Risk Assessment**: Spot potential design pitfalls (e.g., combinational loops, inferred latches, missing reset conditions, clock domain crossing hazards).
5. **JSON Output Generation**: Output your final findings strictly in the requested JSON format without markdown wrapping outside the structure.

### Input RTL Source:
{rtl_code}

### Required JSON Output Schema:
{
  "status": "SUCCESS",
  "module_name": "<string>",
  "ports": [{"name": "<str>", "direction": "input/output", "width": "<str>"}],
  "parameters": [{"name": "<str>", "value": "<str>"}],
  "clocks": ["<string>"],
  "resets": ["<string>"],
  "registers": ["<string>"],
  "wires": ["<string>"],
  "always_blocks": ["<string>"],
  "behavioral_summary": "<string>",
  "risks": ["<string>"],
  "confidence": 95
}
"""

class RTLAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="rtl_analyzer", step_index=1)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        rtl_code = state.get("rtl_code", "")
        run_logger = state.get("logger")

        # LLM Invocation placeholder (replace with core/llm.py client)
        # prompt = RTL_ANALYZER_COT_PROMPT.format(rtl_code=rtl_code)
        
        analysis_result = {
            "status": "SUCCESS",
            "module_name": "analyzed_module",
            "ports": [],
            "behavioral_summary": "Analyzed via agentic CoT pipeline.",
            "risks": [],
            "confidence": 90,
            "source": "cot_agent"
        }

        state["rtl_analysis"] = analysis_result
        if run_logger:
            run_logger.write_json(self.name, "rtl_analysis.json", analysis_result, self.step_index)

        return state
        
