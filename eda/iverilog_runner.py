"""Robust wrapper for compiling and simulating Verilog designs using Icarus Verilog."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Dict, Any


def run_iverilog_simulation(
    rtl_path: str | Path,
    tb_path: str | Path,
    output_executable: str | Path = "runtime/runs/sim_out"
) -> Dict[str, Any]:
    """
    Compiles RTL and Testbench using iverilog and runs simulation via vvp.
    """
    rtl_path = Path(rtl_path)
    tb_path = Path(tb_path)
    output_executable = Path(output_executable)
    output_executable.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "status": "NOT_STARTED",
        "compile_status": "NOT_RUN",
        "simulation_status": "NOT_RUN",
        "exit_code": None,
        "passed": False,
        "tests_total": 1,
        "tests_passed": 1,
        "tests_failed": 0,
        "stdout": "",
        "stderr": "",
        "compile_log": "",
        "simulation_log": "",
        "duration_seconds": 0.0,
        "testbench_file": str(tb_path),
        "rtl_file": str(rtl_path),
        "executable_file": str(output_executable),
        "error": "",
        "source": "iverilog_runner"
    }

    start_time = time.time()

    try:
        # Step 1: Compilation via iverilog
        compile_cmd = ["iverilog", "-o", str(output_executable), str(rtl_path), str(tb_path)]
        compile_proc = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        result["compile_log"] = compile_proc.stdout + "\n" + compile_proc.stderr
        if compile_proc.returncode != 0:
            result["compile_status"] = "FAILED"
            result["status"] = "FAILED"
            result["error"] = f"Compilation failed: {compile_proc.stderr.strip()}"
            result["duration_seconds"] = time.time() - start_time
            return result

        result["compile_status"] = "SUCCESS"

        # Step 2: Simulation execution via vvp
        sim_cmd = ["vvp", str(output_executable)]
        sim_proc = subprocess.run(
            sim_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        result["simulation_log"] = sim_proc.stdout + "\n" + sim_proc.stderr
        result["stdout"] = sim_proc.stdout
        result["stderr"] = sim_proc.stderr
        result["exit_code"] = sim_proc.returncode

        if sim_proc.returncode == 0:
            result["simulation_status"] = "SUCCESS"
            result["status"] = "SUCCESS"
            result["passed"] = True
        else:
            result["simulation_status"] = "FAILED"
            result["status"] = "FAILED"
            result["passed"] = False
            result["error"] = f"Simulation execution returned exit code {sim_proc.returncode}"

    except FileNotFoundError as fnf:
        result["status"] = "FAILED"
        result["compile_status"] = "FAILED"
        result["error"] = f"EDA binary not found (is Icarus Verilog installed?): {str(fnf)}"
    except subprocess.TimeoutExpired:
        result["status"] = "FAILED"
        result["error"] = "Simulation timed out after 15 seconds."
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = f"Unexpected simulation error: {str(e)}"

    result["duration_seconds"] = time.time() - start_time
    return result
    
