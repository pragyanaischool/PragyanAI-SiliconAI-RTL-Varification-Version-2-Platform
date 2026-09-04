"""Deterministic Icarus Verilog runner."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from config.settings import IVERILOG_EXECUTABLE, VVP_EXECUTABLE, SIMULATION_TIMEOUT_SECONDS

class IcarusRunner:
    def run(self, rtl: str, testbench: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="siliconai_") as td:
            root = Path(td)
            rtl_file = root / "design.v"
            tb_file = root / "testbench.v"
            out_file = root / "sim.out"
            rtl_file.write_text(rtl, encoding="utf-8")
            tb_file.write_text(testbench, encoding="utf-8")

            compile_cmd = [IVERILOG_EXECUTABLE, "-g2012", "-o", str(out_file),
                           str(rtl_file), str(tb_file)]
            try:
                cp = subprocess.run(compile_cmd, capture_output=True, text=True,
                                    timeout=SIMULATION_TIMEOUT_SECONDS)
            except FileNotFoundError:
                return {"compile_passed": False, "simulation_passed": False,
                        "compile_output": "iverilog executable not found", "simulation_output": ""}
            except subprocess.TimeoutExpired:
                return {"compile_passed": False, "simulation_passed": False,
                        "compile_output": "Compilation timeout", "simulation_output": ""}

            compile_output = (cp.stdout or "") + (cp.stderr or "")
            if cp.returncode != 0:
                return {"compile_passed": False, "simulation_passed": False,
                        "compile_output": compile_output, "simulation_output": ""}

            try:
                sp = subprocess.run([VVP_EXECUTABLE, str(out_file)],
                                    capture_output=True, text=True,
                                    timeout=SIMULATION_TIMEOUT_SECONDS)
                sim_output = (sp.stdout or "") + (sp.stderr or "")
                return {
                    "compile_passed": True,
                    "simulation_passed": sp.returncode == 0,
                    "compile_output": compile_output,
                    "simulation_output": sim_output,
                    "exit_code": sp.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"compile_passed": True, "simulation_passed": False,
                        "compile_output": compile_output, "simulation_output": "Simulation timeout"}
