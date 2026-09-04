"""
PragyanAI SiliconAI
===================

Central configuration for the Agentic RTL / Verilog Verification Platform.

This file intentionally contains compatibility aliases because different
agents may use slightly different configuration names.

No SymbiYosys dependency is required.

Formal verification is optional and defaults to disabled.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


# ============================================================================
# Environment helpers
# ============================================================================

def _env(name: str, default: Any = None) -> Any:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    if value == "":
        return default

    return value


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = str(_env(name, default)).strip().lower()

    if value in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "enabled",
    }:
        return True

    if value in {
        "0",
        "false",
        "no",
        "n",
        "off",
        "disabled",
    }:
        return False

    return default


# ============================================================================
# Application
# ============================================================================

APP_NAME = _env(
    "APP_NAME",
    "PragyanAI SiliconAI",
)

APP_VERSION = _env(
    "APP_VERSION",
    "1.0.0",
)

APP_DESCRIPTION = _env(
    "APP_DESCRIPTION",
    "Agentic RTL / Verilog Verification Platform",
)


# ============================================================================
# LLM / Groq
# ============================================================================

GROQ_API_KEY = _env(
    "GROQ_API_KEY",
    "",
)

GROQ_MODEL = _env(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

LLM_TEMPERATURE = _env_float(
    "LLM_TEMPERATURE",
    0.2,
)

LLM_MAX_TOKENS = _env_int(
    "LLM_MAX_TOKENS",
    4096,
)

PLANNER_MAX_TOKENS = _env_int(
    "PLANNER_MAX_TOKENS",
    3000,
)

TEST_GENERATOR_MAX_TOKENS = _env_int(
    "TEST_GENERATOR_MAX_TOKENS",
    4000,
)

TESTBENCH_GENERATOR_MAX_TOKENS = _env_int(
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    5000,
)

REPAIR_MAX_TOKENS = _env_int(
    "REPAIR_MAX_TOKENS",
    5000,
)


# ============================================================================
# Demo / execution mode
# ============================================================================

DEMO_MODE = _env_bool(
    "DEMO_MODE",
    False,
)


# ============================================================================
# Input limits
# ============================================================================

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
    30_000,
)

MAX_TESTBENCH_CHARS = _env_int(
    "MAX_TESTBENCH_CHARS",
    100_000,
)


# ============================================================================
# Test generation limits
# ============================================================================

MAX_TEST_SCENARIOS = _env_int(
    "MAX_TEST_SCENARIOS",
    25,
)

MAX_TEST_CASES = _env_int(
    "MAX_TEST_CASES",
    100,
)

MAX_TESTBENCH_LINES = _env_int(
    "MAX_TESTBENCH_LINES",
    1000,
)

MAX_TESTS = _env_int(
    "MAX_TESTS",
    100,
)

MAX_GENERATED_TESTS = _env_int(
    "MAX_GENERATED_TESTS",
    100,
)

MAX_SCENARIOS = _env_int(
    "MAX_SCENARIOS",
    25,
)


# ============================================================================
# Simulation
# ============================================================================

CLOCK_PERIOD_NS = _env_float(
    "CLOCK_PERIOD_NS",
    10.0,
)

TEST_TIMEOUT_NS = _env_int(
    "TEST_TIMEOUT_NS",
    1000,
)

RESET_CYCLES = _env_int(
    "RESET_CYCLES",
    2,
)

# Compatibility aliases
DEFAULT_CLOCK_PERIOD_NS = CLOCK_PERIOD_NS
DEFAULT_TEST_TIMEOUT_NS = TEST_TIMEOUT_NS

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
    "2012",
)

SIM_TIMEOUT = SIMULATION_TIMEOUT_SECONDS


# ============================================================================
# Verification
# ============================================================================

COVERAGE_TARGET = _env_float(
    "COVERAGE_TARGET",
    95.0,
)

MUTATION_TARGET = _env_float(
    "MUTATION_TARGET",
    90.0,
)

VERIFICATION_SCORE_TARGET = _env_float(
    "VERIFICATION_SCORE_TARGET",
    90.0,
)

DEFAULT_MAX_ITERATIONS = _env_int(
    "DEFAULT_MAX_ITERATIONS",
    3,
)

MAX_ITERATIONS = _env_int(
    "MAX_ITERATIONS",
    DEFAULT_MAX_ITERATIONS,
)

MAX_ITERATION = _env_int(
    "MAX_ITERATION",
    MAX_ITERATIONS,
)


# ============================================================================
# Optional verification stages
# ============================================================================

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
    DEFAULT_RUN_MUTATION,
)

ENABLE_FORMAL = _env_bool(
    "ENABLE_FORMAL",
    DEFAULT_RUN_FORMAL,
)

ENABLE_RED_TEAM = _env_bool(
    "ENABLE_RED_TEAM",
    True,
)


# ============================================================================
# Red team
# ============================================================================

RED_TEAM_SCENARIOS = _env_int(
    "RED_TEAM_SCENARIOS",
    10,
)

MAX_RED_TEAM_SCENARIOS = _env_int(
    "MAX_RED_TEAM_SCENARIOS",
    RED_TEAM_SCENARIOS,
)


# ============================================================================
# Mutation
# ============================================================================

MAX_MUTATIONS = _env_int(
    "MAX_MUTATIONS",
    20,
)


# ============================================================================
# Formal verification
# ============================================================================

# Formal backend is intentionally optional.
#
# Supported conceptual values:
#
#     none
#     iverilog
#     yosys
#
# SymbiYosys is intentionally NOT required by this project.

FORMAL_BACKEND = _env(
    "FORMAL_BACKEND",
    "none",
)

FORMAL_TIMEOUT_SECONDS = _env_int(
    "FORMAL_TIMEOUT_SECONDS",
    30,
)


# ============================================================================
# Runtime directories
# ============================================================================

RUNTIME_ROOT = Path(
    _env(
        "RUNTIME_ROOT",
        "runtime",
    )
)

RUN_ROOT = Path(
    _env(
        "RUN_ROOT",
        str(RUNTIME_ROOT / "runs"),
    )
)

LOG_ROOT = Path(
    _env(
        "LOG_ROOT",
        str(RUNTIME_ROOT / "logs"),
    )
)


# ============================================================================
# Logging / artifact retention
# ============================================================================

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

ARTIFACT_RETENTION = _env(
    "ARTIFACT_RETENTION",
    "all",
)


# ============================================================================
# Streamlit
# ============================================================================

STREAMLIT_PAGE_TITLE = _env(
    "STREAMLIT_PAGE_TITLE",
    APP_NAME,
)

STREAMLIT_PAGE_ICON = _env(
    "STREAMLIT_PAGE_ICON",
    "🧪",
)


# ============================================================================
# Directory initialization
# ============================================================================

def ensure_directories() -> None:
    """
    Create required runtime directories.
    """

    directories = [
        RUNTIME_ROOT,
        RUN_ROOT,
        LOG_ROOT,
    ]

    for directory in directories:
        Path(directory).mkdir(
            parents=True,
            exist_ok=True,
        )


# Create directories when configuration is imported.
ensure_directories()


# ============================================================================
# Tool availability
# ============================================================================

def tool_available(tool_name: str) -> bool:
    """
    Return True if an executable is available on PATH.
    """

    if not tool_name:
        return False

    return shutil.which(
        str(tool_name)
    ) is not None


def iverilog_available() -> bool:
    """
    Return whether Icarus Verilog is available.
    """

    return tool_available(
        IVERILOG_EXECUTABLE
    )


def vvp_available() -> bool:
    """
    Return whether VVP is available.
    """

    return tool_available(
        VVP_EXECUTABLE
    )


# ============================================================================
# Validation
# ============================================================================

def validate_settings() -> list[str]:
    """
    Validate configuration.

    Returns a list of human-readable errors.
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

    if MAX_TESTBENCH_LINES <= 0:
        errors.append(
            "MAX_TESTBENCH_LINES must be greater than zero."
        )

    if MAX_ITERATIONS <= 0:
        errors.append(
            "MAX_ITERATIONS must be greater than zero."
        )

    if CLOCK_PERIOD_NS <= 0:
        errors.append(
            "CLOCK_PERIOD_NS must be greater than zero."
        )

    if TEST_TIMEOUT_NS <= 0:
        errors.append(
            "TEST_TIMEOUT_NS must be greater than zero."
        )

    if SIMULATION_TIMEOUT_SECONDS <= 0:
        errors.append(
            "SIMULATION_TIMEOUT_SECONDS must be greater than zero."
        )

    if not RUN_ROOT:
        errors.append(
            "RUN_ROOT is not configured."
        )

    if FORMAL_BACKEND.lower() not in {
        "none",
        "iverilog",
        "yosys",
    }:
        errors.append(
            "FORMAL_BACKEND must be one of: none, iverilog, yosys."
        )

    return errors


SETTINGS_ERRORS = validate_settings()


# ============================================================================
# Settings summary
# ============================================================================

def get_settings_summary() -> Dict[str, Any]:
    """
    Return a safe configuration summary.

    Secrets such as GROQ_API_KEY are never returned.
    """

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "groq_model": GROQ_MODEL,
        "groq_configured": bool(
            GROQ_API_KEY
        ),
        "demo_mode": DEMO_MODE,
        "iverilog_available": iverilog_available(),
        "vvp_available": vvp_available(),
        "clock_period_ns": CLOCK_PERIOD_NS,
        "test_timeout_ns": TEST_TIMEOUT_NS,
        "coverage_target": COVERAGE_TARGET,
        "mutation_target": MUTATION_TARGET,
        "verification_score_target": VERIFICATION_SCORE_TARGET,
        "max_iterations": MAX_ITERATIONS,
        "run_mutation": DEFAULT_RUN_MUTATION,
        "run_formal": DEFAULT_RUN_FORMAL,
        "enable_red_team": ENABLE_RED_TEAM,
        "formal_backend": FORMAL_BACKEND,
        "runtime_root": str(RUNTIME_ROOT),
        "run_root": str(RUN_ROOT),
        "log_root": str(LOG_ROOT),
    }


__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_DESCRIPTION",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "PLANNER_MAX_TOKENS",
    "TEST_GENERATOR_MAX_TOKENS",
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    "REPAIR_MAX_TOKENS",
    "DEMO_MODE",
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
    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_SCORE_TARGET",
    "DEFAULT_MAX_ITERATIONS",
    "MAX_ITERATIONS",
    "MAX_ITERATION",
    "DEFAULT_RUN_MUTATION",
    "DEFAULT_RUN_FORMAL",
    "ENABLE_MUTATION",
    "ENABLE_FORMAL",
    "ENABLE_RED_TEAM",
    "RED_TEAM_SCENARIOS",
    "MAX_RED_TEAM_SCENARIOS",
    "MAX_MUTATIONS",
    "FORMAL_BACKEND",
    "FORMAL_TIMEOUT_SECONDS",
    "RUNTIME_ROOT",
    "RUN_ROOT",
    "LOG_ROOT",
    "WRITE_AGENT_LOGS",
    "WRITE_WORKFLOW_LOG",
    "WRITE_RUN_MANIFEST",
    "ARTIFACT_RETENTION",
    "STREAMLIT_PAGE_TITLE",
    "STREAMLIT_PAGE_ICON",
    "ensure_directories",
    "tool_available",
    "iverilog_available",
    "vvp_available",
    "validate_settings",
    "get_settings_summary",
    "SETTINGS_ERRORS",
]

