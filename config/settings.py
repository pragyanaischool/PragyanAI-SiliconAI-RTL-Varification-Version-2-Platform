"""
PragyanAI SiliconAI
===================

Central application configuration.

Important design rules
----------------------

1. No agent should hard-code an LLM model.
2. No agent should hard-code simulator paths.
3. Streamlit Cloud secrets and environment variables are supported.
4. The application must remain usable when Groq is unavailable.
5. Formal verification is optional.
6. SymbiYosys is intentionally NOT required.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _streamlit_secret(name: str, default: Any = None) -> Any:
    """
    Safely read a Streamlit secret.

    Streamlit is optional at import time, so this function never makes
    Streamlit a hard dependency of the configuration module.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    return default


def _env(name: str, default: Any = None) -> Any:
    """
    Resolve configuration using:

        environment variable
        -> Streamlit secret
        -> default
    """
    value = os.getenv(name)

    if value is not None and str(value).strip() != "":
        return value

    secret = _streamlit_secret(name)

    if secret is not None and str(secret).strip() != "":
        return secret

    return default


def _env_int(name: str, default: int) -> int:
    value = _env(name, default)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    value = _env(name, default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name, default)

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in {"1", "true", "yes", "y", "on"}:
        return True

    if text in {"0", "false", "no", "n", "off"}:
        return False

    return default


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

APP_NAME = _env(
    "APP_NAME",
    "PragyanAI SiliconAI",
)

APP_VERSION = _env(
    "APP_VERSION",
    "1.1.0",
)

APP_DESCRIPTION = _env(
    "APP_DESCRIPTION",
    "Agentic RTL / Verilog Verification Platform",
)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

# IMPORTANT:
#
# The previous deployment used:
#
#     llama-3.3-70b-versatile
#
# and the deployed API key returned model_not_found.
#
# Keep the model configurable and use a current production model by default.
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

GROQ_API_KEY = _env(
    "GROQ_API_KEY",
    "",
)

GROQ_MODEL = _env(
    "GROQ_MODEL",
    DEFAULT_GROQ_MODEL,
)

LLM_TEMPERATURE = _env_float(
    "LLM_TEMPERATURE",
    0.1,
)

LLM_MAX_TOKENS = _env_int(
    "LLM_MAX_TOKENS",
    4096,
)

PLANNER_MAX_TOKENS = _env_int(
    "PLANNER_MAX_TOKENS",
    4096,
)

TEST_GENERATOR_MAX_TOKENS = _env_int(
    "TEST_GENERATOR_MAX_TOKENS",
    8192,
)

TESTBENCH_GENERATOR_MAX_TOKENS = _env_int(
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    8192,
)

REPAIR_MAX_TOKENS = _env_int(
    "REPAIR_MAX_TOKENS",
    8192,
)


# ---------------------------------------------------------------------------
# Input limits
# ---------------------------------------------------------------------------

MAX_RTL_CHARS = _env_int(
    "MAX_RTL_CHARS",
    100_000,
)

MAX_RTL_CHARS_FOR_LLM = _env_int(
    "MAX_RTL_CHARS_FOR_LLM",
    30_000,
)

MAX_SPEC_CHARS = _env_int(
    "MAX_SPEC_CHARS",
    50_000,
)

MAX_TESTBENCH_CHARS = _env_int(
    "MAX_TESTBENCH_CHARS",
    100_000,
)

MAX_TEST_SCENARIOS = _env_int(
    "MAX_TEST_SCENARIOS",
    20,
)

MAX_TEST_CASES = _env_int(
    "MAX_TEST_CASES",
    50,
)

MAX_TESTBENCH_LINES = _env_int(
    "MAX_TESTBENCH_LINES",
    2_000,
)

MAX_TESTS = _env_int(
    "MAX_TESTS",
    50,
)

MAX_GENERATED_TESTS = _env_int(
    "MAX_GENERATED_TESTS",
    50,
)

MAX_SCENARIOS = _env_int(
    "MAX_SCENARIOS",
    20,
)


# ---------------------------------------------------------------------------
# Clock / simulation
# ---------------------------------------------------------------------------

CLOCK_PERIOD_NS = _env_float(
    "CLOCK_PERIOD_NS",
    10.0,
)

TEST_TIMEOUT_NS = _env_int(
    "TEST_TIMEOUT_NS",
    100_000,
)

RESET_CYCLES = _env_int(
    "RESET_CYCLES",
    2,
)

DEFAULT_CLOCK_PERIOD_NS = _env_float(
    "DEFAULT_CLOCK_PERIOD_NS",
    CLOCK_PERIOD_NS,
)

DEFAULT_TEST_TIMEOUT_NS = _env_int(
    "DEFAULT_TEST_TIMEOUT_NS",
    TEST_TIMEOUT_NS,
)

IVERILOG_EXECUTABLE = _env(
    "IVERILOG_EXECUTABLE",
    "iverilog",
)

VVP_EXECUTABLE = _env(
    "VVP_EXECUTABLE",
    "vvp",
)

SIMULATION_TIMEOUT_SECONDS = _env_int(
    "SIMULATION_TIMEOUT_SECONDS",
    30,
)

COMPILE_TIMEOUT_SECONDS = _env_int(
    "COMPILE_TIMEOUT_SECONDS",
    30,
)

SIMULATION_STANDARD = _env(
    "SIMULATION_STANDARD",
    "2005-sv",
)

SIM_TIMEOUT = _env_int(
    "SIM_TIMEOUT",
    SIMULATION_TIMEOUT_SECONDS,
)


# ---------------------------------------------------------------------------
# Verification targets
# ---------------------------------------------------------------------------

COVERAGE_TARGET = _env_float(
    "COVERAGE_TARGET",
    90.0,
)

MUTATION_TARGET = _env_float(
    "MUTATION_TARGET",
    80.0,
)

VERIFICATION_SCORE_TARGET = _env_float(
    "VERIFICATION_SCORE_TARGET",
    90.0,
)


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------

DEFAULT_MAX_ITERATIONS = _env_int(
    "DEFAULT_MAX_ITERATIONS",
    2,
)

MAX_ITERATIONS = _env_int(
    "MAX_ITERATIONS",
    5,
)

MAX_ITERATION = _env_int(
    "MAX_ITERATION",
    MAX_ITERATIONS,
)


# ---------------------------------------------------------------------------
# Optional verification stages
# ---------------------------------------------------------------------------

DEFAULT_RUN_MUTATION = _env_bool(
    "DEFAULT_RUN_MUTATION",
    True,
)

DEFAULT_RUN_FORMAL = _env_bool(
    "DEFAULT_RUN_FORMAL",
    False,
)

ENABLE_MUTATION = _env_bool(
    "ENABLE_MUTATION",
    True,
)

ENABLE_FORMAL = _env_bool(
    "ENABLE_FORMAL",
    False,
)

ENABLE_RED_TEAM = _env_bool(
    "ENABLE_RED_TEAM",
    True,
)

RED_TEAM_SCENARIOS = _env_int(
    "RED_TEAM_SCENARIOS",
    8,
)

MAX_RED_TEAM_SCENARIOS = _env_int(
    "MAX_RED_TEAM_SCENARIOS",
    20,
)

MAX_MUTATIONS = _env_int(
    "MAX_MUTATIONS",
    10,
)


# ---------------------------------------------------------------------------
# Formal verification
# ---------------------------------------------------------------------------

# SymbiYosys is deliberately not part of this project.

FORMAL_BACKEND = _env(
    "FORMAL_BACKEND",
    "none",
)

FORMAL_TIMEOUT_SECONDS = _env_int(
    "FORMAL_TIMEOUT_SECONDS",
    30,
)


# ---------------------------------------------------------------------------
# Runtime directories
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent

RUNTIME_ROOT = Path(
    _env(
        "RUNTIME_ROOT",
        PROJECT_ROOT / "runtime",
    )
)

RUN_ROOT = Path(
    _env(
        "RUN_ROOT",
        RUNTIME_ROOT / "runs",
    )
)

LOG_ROOT = Path(
    _env(
        "LOG_ROOT",
        RUNTIME_ROOT / "logs",
    )
)

REPORT_ROOT = Path(
    _env(
        "REPORT_ROOT",
        PROJECT_ROOT / "reports",
    )
)


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

WRITE_AGENT_LOGS = _env_bool(
    "WRITE_AGENT_LOGS",
    True,
)

WRITE_WORKFLOW_LOG = _env_bool(
    "WRITE_WORKFLOW_LOG",
    True,
)

WRITE_RUN_MANIFEST = _env_bool(
    "WRITE_RUN_MANIFEST",
    True,
)

ARTIFACT_RETENTION = _env_int(
    "ARTIFACT_RETENTION",
    50,
)


# ---------------------------------------------------------------------------
# Streamlit
# ---------------------------------------------------------------------------

STREAMLIT_PAGE_TITLE = _env(
    "STREAMLIT_PAGE_TITLE",
    "PragyanAI SiliconAI",
)

STREAMLIT_PAGE_ICON = _env(
    "STREAMLIT_PAGE_ICON",
    "🧪",
)


# ---------------------------------------------------------------------------
# Directory initialization
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    """
    Create application runtime directories.

    This function is intentionally safe to call repeatedly.
    """

    directories = [
        RUNTIME_ROOT,
        RUN_ROOT,
        LOG_ROOT,
        REPORT_ROOT,
    ]

    for directory in directories:
        Path(directory).mkdir(
            parents=True,
            exist_ok=True,
        )


# Initialize runtime folders when configuration is imported.
ensure_directories()


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------

def tool_available(executable: str) -> bool:
    """
    Return True when an executable is available on PATH.
    """
    if not executable:
        return False

    return shutil.which(str(executable)) is not None


def iverilog_available() -> bool:
    """
    Check whether Icarus Verilog is installed.
    """
    return tool_available(
        str(IVERILOG_EXECUTABLE)
    )


def vvp_available() -> bool:
    """
    Check whether VVP is installed.
    """
    return tool_available(
        str(VVP_EXECUTABLE)
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_settings() -> list[str]:
    """
    Validate configuration.

    Returns a list of human-readable problems.

    Missing GROQ_API_KEY is intentionally not treated as fatal because
    the application has deterministic fallback behavior.
    """

    errors: list[str] = []

    if MAX_RTL_CHARS <= 0:
        errors.append(
            "MAX_RTL_CHARS must be greater than zero."
        )

    if MAX_SPEC_CHARS <= 0:
        errors.append(
            "MAX_SPEC_CHARS must be greater than zero."
        )

    if MAX_TEST_SCENARIOS <= 0:
        errors.append(
            "MAX_TEST_SCENARIOS must be greater than zero."
        )

    if MAX_TEST_CASES <= 0:
        errors.append(
            "MAX_TEST_CASES must be greater than zero."
        )

    if CLOCK_PERIOD_NS <= 0:
        errors.append(
            "CLOCK_PERIOD_NS must be greater than zero."
        )

    if SIMULATION_TIMEOUT_SECONDS <= 0:
        errors.append(
            "SIMULATION_TIMEOUT_SECONDS must be greater than zero."
        )

    if DEFAULT_MAX_ITERATIONS <= 0:
        errors.append(
            "DEFAULT_MAX_ITERATIONS must be greater than zero."
        )

    if MAX_ITERATIONS <= 0:
        errors.append(
            "MAX_ITERATIONS must be greater than zero."
        )

    if not str(GROQ_MODEL).strip():
        errors.append(
            "GROQ_MODEL cannot be empty."
        )

    return errors


SETTINGS_ERRORS = validate_settings()


# ---------------------------------------------------------------------------
# Settings summary
# ---------------------------------------------------------------------------

def get_settings_summary() -> dict[str, Any]:
    """
    Return a safe configuration summary.

    Secrets are never returned.
    """

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,

        "groq_configured": bool(
            str(GROQ_API_KEY).strip()
        ),

        "groq_model": GROQ_MODEL,

        "llm_temperature": LLM_TEMPERATURE,
        "llm_max_tokens": LLM_MAX_TOKENS,

        "iverilog": str(
            IVERILOG_EXECUTABLE
        ),

        "vvp": str(
            VVP_EXECUTABLE
        ),

        "iverilog_available": iverilog_available(),
        "vvp_available": vvp_available(),

        "coverage_target": COVERAGE_TARGET,
        "mutation_target": MUTATION_TARGET,
        "verification_score_target": VERIFICATION_SCORE_TARGET,

        "default_max_iterations": DEFAULT_MAX_ITERATIONS,
        "max_iterations": MAX_ITERATIONS,

        "run_mutation": DEFAULT_RUN_MUTATION,
        "run_formal": DEFAULT_RUN_FORMAL,
        "enable_red_team": ENABLE_RED_TEAM,

        "formal_backend": FORMAL_BACKEND,

        "runtime_root": str(RUNTIME_ROOT),
        "run_root": str(RUN_ROOT),
        "log_root": str(LOG_ROOT),

        "settings_errors": list(
            SETTINGS_ERRORS
        ),
    }


__all__ = [
    # Application
    "APP_NAME",
    "APP_VERSION",
    "APP_DESCRIPTION",

    # LLM
    "DEFAULT_GROQ_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "PLANNER_MAX_TOKENS",
    "TEST_GENERATOR_MAX_TOKENS",
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    "REPAIR_MAX_TOKENS",

    # Input limits
    "MAX_RTL_CHARS",
    "MAX_RTL_CHARS_FOR_LLM",
    "MAX_SPEC_CHARS",
    "MAX_TESTBENCH_CHARS",
    "MAX_TEST_SCENARIOS",
    "MAX_TEST_CASES",
    "MAX_TESTBENCH_LINES",
    "MAX_TESTS",
    "MAX_GENERATED_TESTS",
    "MAX_SCENARIOS",

    # Simulation
    "CLOCK_PERIOD_NS",
    "TEST_TIMEOUT_NS",
    "RESET_CYCLES",
    "DEFAULT_CLOCK_PERIOD_NS",
    "DEFAULT_TEST_TIMEOUT_NS",
    "IVERILOG_EXECUTABLE",
    "VVP_EXECUTABLE",
    "SIMULATION_TIMEOUT_SECONDS",
    "COMPILE_TIMEOUT_SECONDS",
    "SIMULATION_STANDARD",
    "SIM_TIMEOUT",

    # Verification
    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_SCORE_TARGET",

    # Iterations
    "DEFAULT_MAX_ITERATIONS",
    "MAX_ITERATIONS",
    "MAX_ITERATION",

    # Optional stages
    "DEFAULT_RUN_MUTATION",
    "DEFAULT_RUN_FORMAL",
    "ENABLE_MUTATION",
    "ENABLE_FORMAL",
    "ENABLE_RED_TEAM",
    "RED_TEAM_SCENARIOS",
    "MAX_RED_TEAM_SCENARIOS",
    "MAX_MUTATIONS",

    # Formal
    "FORMAL_BACKEND",
    "FORMAL_TIMEOUT_SECONDS",

    # Runtime
    "PROJECT_ROOT",
    "RUNTIME_ROOT",
    "RUN_ROOT",
    "LOG_ROOT",
    "REPORT_ROOT",

    # Logging
    "WRITE_AGENT_LOGS",
    "WRITE_WORKFLOW_LOG",
    "WRITE_RUN_MANIFEST",
    "ARTIFACT_RETENTION",

    # Streamlit
    "STREAMLIT_PAGE_TITLE",
    "STREAMLIT_PAGE_ICON",

    # Functions
    "ensure_directories",
    "tool_available",
    "iverilog_available",
    "vvp_available",
    "validate_settings",
    "get_settings_summary",
    "SETTINGS_ERRORS",
]


