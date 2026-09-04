"""Central configuration for PragyanAI SiliconAI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = BASE_DIR / "runtime"
RUNS_DIR = RUNTIME_DIR / "runs"

APP_NAME = "PragyanAI SiliconAI"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Agentic RTL Verification Platform"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
DEFAULT_MODEL = GROQ_MODEL
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
DEFAULT_TEMPERATURE = LLM_TEMPERATURE
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1800"))
DEFAULT_MAX_TOKENS = LLM_MAX_TOKENS

MAX_RTL_CHARS = int(os.getenv("MAX_RTL_CHARS", "12000"))
MAX_SPECIFICATION_CHARS = int(os.getenv("MAX_SPECIFICATION_CHARS", "8000"))
MAX_SIMULATION_OUTPUT_CHARS = int(os.getenv("MAX_SIMULATION_OUTPUT_CHARS", "8000"))
MAX_TESTBENCH_CHARS = int(os.getenv("MAX_TESTBENCH_CHARS", "12000"))

MAX_TEST_SCENARIOS = int(os.getenv("MAX_TEST_SCENARIOS", "20"))
MAX_TEST_CASES = int(os.getenv("MAX_TEST_CASES", "30"))
MAX_TESTBENCH_LINES = int(os.getenv("MAX_TESTBENCH_LINES", "1200"))
MAX_TESTS = MAX_TEST_CASES
MAX_GENERATED_TESTS = MAX_TEST_CASES

DEFAULT_CLOCK_PERIOD_NS = int(os.getenv("DEFAULT_CLOCK_PERIOD_NS", "10"))
DEFAULT_RESET_CYCLES = int(os.getenv("DEFAULT_RESET_CYCLES", "2"))
DEFAULT_TEST_TIMEOUT_NS = int(os.getenv("DEFAULT_TEST_TIMEOUT_NS", "1000"))

COVERAGE_TARGET = float(os.getenv("COVERAGE_TARGET", "95"))
MUTATION_TARGET = float(os.getenv("MUTATION_TARGET", "90"))
VERIFICATION_SCORE_TARGET = float(os.getenv("VERIFICATION_SCORE_TARGET", "90"))

DEFAULT_MAX_ITERATIONS = int(os.getenv("DEFAULT_MAX_ITERATIONS", "3"))
MIN_ITERATIONS = int(os.getenv("MIN_ITERATIONS", "1"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))

RED_TEAM_ENABLED_BY_DEFAULT = os.getenv("RED_TEAM_ENABLED_BY_DEFAULT", "true").lower() in {"1","true","yes","on"}
MUTATION_ENABLED_BY_DEFAULT = os.getenv("MUTATION_ENABLED_BY_DEFAULT", "true").lower() in {"1","true","yes","on"}
FORMAL_ENABLED_BY_DEFAULT = os.getenv("FORMAL_ENABLED_BY_DEFAULT", "false").lower() in {"1","true","yes","on"}
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1","true","yes","on"}

IVERILOG_EXECUTABLE = os.getenv("IVERILOG_EXECUTABLE", "iverilog")
VVP_EXECUTABLE = os.getenv("VVP_EXECUTABLE", "vvp")
SIMULATION_TIMEOUT_SECONDS = int(os.getenv("SIMULATION_TIMEOUT_SECONDS", "30"))

def ensure_directories() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

def tool_available(name: str) -> bool:
    return bool(name and shutil.which(name))

ensure_directories()
