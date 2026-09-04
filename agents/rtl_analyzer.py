from __future__ import annotations
import re
from .base import BaseAgent
from core.state import VerificationState
from config.settings import MAX_RTL_CHARS

class RTLAnalyzerAgent(BaseAgent):
    name = "RTL Analysis"
    step = 1

    def run(self, state: VerificationState):
        rtl = (state.get("current_rtl") or state.get("rtl_code") or "")[:MAX_RTL_CHARS]
        modules = re.findall(r"\bmodule\s+(\w+)", rtl)
        inputs = re.findall(r"\binput\b[^;]*\b(\w+)\s*(?:,|;)", rtl)
        outputs = re.findall(r"\boutput\b[^;]*\b(\w+)\s*(?:,|;)", rtl)
        analysis = {
            "module_names": modules,
            "input_candidates": inputs,
            "output_candidates": outputs,
            "clocked": bool(re.search(r"always_ff|posedge|negedge", rtl)),
            "reset_present": bool(re.search(r"\breset\b|\brst\b", rtl, re.I)),
            "always_blocks": len(re.findall(r"\balways\b", rtl)),
            "line_count": len(rtl.splitlines()),
            "verification_points": [
                "reset behavior",
                "normal operation",
                "boundary conditions",
                "invalid/edge stimulus",
            ],
        }
        return {"rtl_analysis": analysis}
