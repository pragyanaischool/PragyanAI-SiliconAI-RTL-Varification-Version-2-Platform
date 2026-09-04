"""Icarus Verilog and VVP execution runner wrapper."""

from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Any, Dict, Optional


def run_iverilog_simulation(
    rtl_path: str | Path,
    tb_path: str | Path,
    output_executable: str | Path = "runtime/runs/sim_out",
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """
    Compile RTL and testbench using Icarus Verilog (iverilog) 
    and execute the simulation using VVP.
    """
    rtl_p = Path(rtl_path)
    tb_p = Path(tb_path)
    out_p = Path(output_executable)

    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not rtl_p.exists():
        return {
            "passed": False,
            "stage": "compilation",
            "compile_status": "FAILED",
            "simulation_status": "NOT_RUN",
            "error": f"RTL file not found: {rtl_p}",
            "compile_log": "",
            "simulation_log": "",
        }

    if not tb_p.exists():
        return {
            "passed": False,
            "stage": "compilation",
            "compile_status": "FAILED",
            "simulation_status": "NOT_RUN",
            "error": f"Testbench file not found: {tb_p}",
            "compile_log": "",
            "simulation_log": "",
        }

    # 1. Compilation Step
    compile_cmd = ["iverilog", "-o", str(out_p), str(rtl_p), str(tb_p)]
    try:
        compile_proc = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "stage": "compilation",
            "compile_status": "TIMEOUT",
            "simulation_status": "NOT_RUN",
            "error": "Iverilog compilation timed out.",
            "compile_log": "",
            "simulation_log": "",
        }
    except Exception as e:
        return {
            "passed": False,
            "stage": "compilation",
            "compile_status": "ERROR",
            "simulation_status": "NOT_RUN",
            "error": str(e),
            "compile_log": "",
            "simulation_log": "",
        }

    compile_log = compile_proc.stdout + "\n" + compile_proc.stderr

    if compile_proc.returncode != 0:
        return {
            "passed": False,
            "stage": "compilation",
            "compile_status": "FAILED",
            "simulation_status": "NOT_RUN",
            "error": "Compilation failed with syntax or binding errors.",
            "compile_log": compile_log,
            "simulation_log": "",
            "exit_code": compile_proc.returncode,
        }

    # 2. Simulation Execution Step (VVP)
    run_cmd = ["vvp", str(out_p)]
    try:
        run_proc = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "stage": "simulation",
            "compile_status": "SUCCESS",
            "simulation_status": "TIMEOUT",
            "error": "Simulation execution timed out.",
            "compile_log": compile_log,
            "simulation_log": "",
        }
    except Exception as e:
        return {
            "passed": False,
            "stage": "simulation",
            "compile_status": "SUCCESS",
            "simulation_status": "ERROR",
            "error": str(e),
            "compile_log": compile_log,
            "simulation_log": "",
        }

    sim_log = run_proc.stdout + "\n" + run_proc.stderr
    passed = run_proc.returncode == 0

    return {
        "passed": passed,
        "stage": "complete",
        "compile_status": "SUCCESS",
        "simulation_status": "SUCCESS" if passed else "FAILED",
        "exit_code": run_proc.returncode,
        "compile_log": compile_log,
        "simulation_log": sim_log,
        "stdout": run_proc.stdout,
        "stderr": run_proc.stderr,
        "testbench_file": str(tb_p),
        "rtl_file": str(rtl_p),
        "executable_file": str(out_p),
    }
    
