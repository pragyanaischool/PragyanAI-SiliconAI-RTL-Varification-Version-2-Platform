"""
PragyanAI SiliconAI
===================

Central configuration for the Agentic RTL / Verilog Verification
Platform.

This file is intentionally self-contained so that all agents,
LangGraph workflow nodes, EDA runners, observability components,
and Streamlit UI use the same configuration source.

Environment variables
---------------------
Values can be overridden through environment variables or a .env file.

Example:

    GROQ_API_KEY=your_key
    GROQ_MODEL=openai/gpt-oss-120b
    DEMO_MODE=false

No SymbiYosys dependency is required by this configuration.
"""

from __future__ import annotations

import os
from pathlib import Path


# ============================================================================
# Project Paths
# ============================================================================

# config/settings.py
CONFIG_DIR = Path(__file__).resolve().parent

# Project root:
# <project>/
#     config/
#         settings.py
PROJECT_ROOT = CONFIG_DIR.parent


# ============================================================================
# Helper Functions
# ============================================================================


def _env(
    name: str,
    default: str,
) -> str:
    """
    Read a string environment variable.

    Empty values are treated as the supplied default.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip()


def _env_int(
    name: str,
    default: int,
) -> int:
    """
    Read an integer environment variable safely.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value)

    except ValueError:
        return default


def _env_float(
    name: str,
    default: float,
) -> float:
    """
    Read a floating-point environment variable safely.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return float(value)

    except ValueError:
        return default


def _env_bool(
    name: str,
    default: bool,
) -> bool:
    """
    Read a boolean environment variable safely.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


# ============================================================================
# Application Identity
# ============================================================================

APP_NAME = _env(
    "APP_NAME",
    "PragyanAI SiliconAI",
)

APP_VERSION = _env(
    "APP_VERSION",
    "2.0.0",
)

APP_DESCRIPTION = _env(
    "APP_DESCRIPTION",
    "Agentic RTL / Verilog Verification Platform",
)


# ============================================================================
# LLM / Groq Configuration
# ============================================================================

GROQ_API_KEY = _env(
    "GROQ_API_KEY",
    "",
)

GROQ_MODEL = _env(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

LLM_TEMPERATURE = _env_float(
    "LLM_TEMPERATURE",
    0.1,
)

LLM_MAX_TOKENS = _env_int(
    "LLM_MAX_TOKENS",
    1800,
)

# Backward-compatible aliases that older agents may use.

PLANNER_MAX_TOKENS = _env_int(
    "PLANNER_MAX_TOKENS",
    LLM_MAX_TOKENS,
)

TEST_GENERATOR_MAX_TOKENS = _env_int(
    "TEST_GENERATOR_MAX_TOKENS",
    LLM_MAX_TOKENS,
)

TESTBENCH_GENERATOR_MAX_TOKENS = _env_int(
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    LLM_MAX_TOKENS,
)

REPAIR_MAX_TOKENS = _env_int(
    "REPAIR_MAX_TOKENS",
    LLM_MAX_TOKENS,
)


# ============================================================================
# Demo / Offline Mode
# ============================================================================

DEMO_MODE = _env_bool(
    "DEMO_MODE",
    False,
)


# ============================================================================
# RTL / Specification Limits
# ============================================================================

MAX_RTL_CHARS = _env_int(
    "MAX_RTL_CHARS",
    50000,
)

MAX_RTL_CHARS_FOR_LLM = _env_int(
    "MAX_RTL_CHARS_FOR_LLM",
    30000,
)

MAX_SPEC_CHARS = _env_int(
    "MAX_SPEC_CHARS",
    30000,
)

MAX_TESTBENCH_CHARS = _env_int(
    "MAX_TESTBENCH_CHARS",
    50000,
)


# ============================================================================
# Test Generation Limits
# ============================================================================

MAX_TEST_SCENARIOS = _env_int(
    "MAX_TEST_SCENARIOS",
    20,
)

MAX_TEST_CASES = _env_int(
    "MAX_TEST_CASES",
    30,
)

MAX_TESTBENCH_LINES = _env_int(
    "MAX_TESTBENCH_LINES",
    1200,
)

# Compatibility aliases.
#
# Different generations of the project used different names.
# Keeping these aliases prevents import failures when older agents
# are still present in the repository.

MAX_TESTS = MAX_TEST_CASES

MAX_GENERATED_TESTS = MAX_TEST_CASES

MAX_SCENARIOS = MAX_TEST_SCENARIOS


# ============================================================================
# Verification Targets
# ============================================================================

COVERAGE_TARGET = _env_int(
    "COVERAGE_TARGET",
    95,
)

MUTATION_TARGET = _env_int(
    "MUTATION_TARGET",
    90,
)

VERIFICATION_SCORE_TARGET = _env_int(
    "VERIFICATION_SCORE_TARGET",
    90,
)


# ============================================================================
# Iteration / Agentic Loop Configuration
# ============================================================================

DEFAULT_MAX_ITERATIONS = _env_int(
    "DEFAULT_MAX_ITERATIONS",
    3,
)

MAX_ITERATIONS = _env_int(
    "MAX_ITERATIONS",
    10,
)


# ============================================================================
# Feature Flags
# ============================================================================

# Mutation testing is enabled from the UI by default according to this
# setting. It can be overridden through environment variables.

DEFAULT_RUN_MUTATION = _env_bool(
    "DEFAULT_RUN_MUTATION",
    False,
)

# Formal verification is intentionally disabled by default.
#
# The project does NOT require SymbiYosys.
#
# If a formal backend is later integrated, the feature can be enabled
# without changing the rest of the configuration architecture.

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


# ============================================================================
# Simulation Configuration
# ============================================================================

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


# ============================================================================
# Testbench Defaults
# ============================================================================

CLOCK_PERIOD_NS = _env_int(
    "CLOCK_PERIOD_NS",
    10,
)

RESET_CYCLES = _env_int(
    "RESET_CYCLES",
    2,
)

TEST_TIMEOUT_NS = _env_int(
    "TEST_TIMEOUT_NS",
    10000,
)


# ============================================================================
# Red-Team Configuration
# ============================================================================

RED_TEAM_SCENARIOS = _env_int(
    "RED_TEAM_SCENARIOS",
    8,
)

MAX_RED_TEAM_SCENARIOS = _env_int(
    "MAX_RED_TEAM_SCENARIOS",
    RED_TEAM_SCENARIOS,
)


# ============================================================================
# Mutation Configuration
# ============================================================================

MAX_MUTATIONS = _env_int(
    "MAX_MUTATIONS",
    20,
)


# ============================================================================
# Formal Configuration
# ============================================================================

# No SymbiYosys dependency is assumed.

FORMAL_TIMEOUT_SECONDS = _env_int(
    "FORMAL_TIMEOUT_SECONDS",
    60,
)

FORMAL_BACKEND = _env(
    "FORMAL_BACKEND",
    "none",
)


# ============================================================================
# Observability / Runtime
# ============================================================================

RUNTIME_ROOT = Path(
    _env(
        "RUNTIME_ROOT",
        str(PROJECT_ROOT / "runtime"),
    )
)

RUN_ROOT = Path(
    _env(
        "RUN_ROOT",
        str(RUNTIME_ROOT / "runs"),
    )
)

# Compatibility alias used by older versions of the workflow.

LOG_ROOT = Path(
    _env(
        "LOG_ROOT",
        str(RUNTIME_ROOT / "logs"),
    )
)


# ============================================================================
# Artifact Configuration
# ============================================================================

ARTIFACT_RETENTION = _env_int(
    "ARTIFACT_RETENTION",
    100,
)

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


# ============================================================================
# Streamlit Configuration
# ============================================================================

STREAMLIT_PAGE_TITLE = _env(
    "STREAMLIT_PAGE_TITLE",
    f"{APP_NAME} | Agentic RTL Verification",
)

STREAMLIT_PAGE_ICON = _env(
    "STREAMLIT_PAGE_ICON",
    "🔬",
)


# ============================================================================
# Directory Helpers
# ============================================================================


def ensure_directories() -> None:
    """
    Create runtime directories required by the platform.

    This function is safe to call multiple times.
    """

    directories = [
        RUNTIME_ROOT,
        RUN_ROOT,
        LOG_ROOT,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================================
# Tool Availability
# ============================================================================


def tool_available(
    executable: str,
) -> bool:
    """
    Check whether an executable is available on PATH.

    Example:

        if tool_available("iverilog"):
            ...
    """

    import shutil

    return shutil.which(executable) is not None


def iverilog_available() -> bool:
    """Return True when Icarus Verilog is installed."""
    return tool_available(
        IVERILOG_EXECUTABLE
    )


def vvp_available() -> bool:
    """Return True when VVP is installed."""
    return tool_available(
        VVP_EXECUTABLE
    )


# ============================================================================
# Configuration Validation
# ============================================================================


def validate_settings() -> list[str]:
    """
    Validate configuration values.

    Returns
    -------
    list[str]
        Human-readable configuration problems.

    An empty list means the configuration is valid.
    """

    errors: list[str] = []

    if not APP_NAME:
        errors.append(
            "APP_NAME cannot be empty."
        )

    if LLM_TEMPERATURE < 0:
        errors.append(
            "LLM_TEMPERATURE cannot be negative."
        )

    if LLM_MAX_TOKENS <= 0:
        errors.append(
            "LLM_MAX_TOKENS must be greater than zero."
        )

    if MAX_RTL_CHARS <= 0:
        errors.append(
            "MAX_RTL_CHARS must be greater than zero."
        )

    if MAX_TEST_SCENARIOS <= 0:
        errors.append(
            "MAX_TEST_SCENARIOS must be greater than zero."
        )

    if MAX_TEST_CASES <= 0:
        errors.append(
            "MAX_TEST_CASES must be greater than zero."
        )

    if MAX_TESTBENCH_LINES <= 0:
        errors.append(
            "MAX_TESTBENCH_LINES must be greater than zero."
        )

    if COVERAGE_TARGET < 0 or COVERAGE_TARGET > 100:
        errors.append(
            "COVERAGE_TARGET must be between 0 and 100."
        )

    if MUTATION_TARGET < 0 or MUTATION_TARGET > 100:
        errors.append(
            "MUTATION_TARGET must be between 0 and 100."
        )

    if (
        VERIFICATION_SCORE_TARGET < 0
        or VERIFICATION_SCORE_TARGET > 100
    ):
        errors.append(
            "VERIFICATION_SCORE_TARGET must be "
            "between 0 and 100."
        )

    if DEFAULT_MAX_ITERATIONS <= 0:
        errors.append(
            "DEFAULT_MAX_ITERATIONS must be greater than zero."
        )

    if SIMULATION_TIMEOUT_SECONDS <= 0:
        errors.append(
            "SIMULATION_TIMEOUT_SECONDS must be greater than zero."
        )

    if COMPILE_TIMEOUT_SECONDS <= 0:
        errors.append(
            "COMPILE_TIMEOUT_SECONDS must be greater than zero."
        )

    return errors


# ============================================================================
# Configuration Summary
# ============================================================================


def get_settings_summary() -> dict[str, object]:
    """
    Return a safe configuration summary.

    Secrets such as GROQ_API_KEY are deliberately excluded.
    """

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "demo_mode": DEMO_MODE,
        "groq_model": GROQ_MODEL,
        "llm_temperature": LLM_TEMPERATURE,
        "llm_max_tokens": LLM_MAX_TOKENS,
        "max_rtl_chars": MAX_RTL_CHARS,
        "max_test_scenarios": MAX_TEST_SCENARIOS,
        "max_test_cases": MAX_TEST_CASES,
        "max_testbench_lines": MAX_TESTBENCH_LINES,
        "coverage_target": COVERAGE_TARGET,
        "mutation_target": MUTATION_TARGET,
        "verification_score_target": (
            VERIFICATION_SCORE_TARGET
        ),
        "default_max_iterations": (
            DEFAULT_MAX_ITERATIONS
        ),
        "default_run_mutation": (
            DEFAULT_RUN_MUTATION
        ),
        "default_run_formal": (
            DEFAULT_RUN_FORMAL
        ),
        "enable_mutation": ENABLE_MUTATION,
        "enable_formal": ENABLE_FORMAL,
        "enable_red_team": ENABLE_RED_TEAM,
        "iverilog_executable": (
            IVERILOG_EXECUTABLE
        ),
        "vvp_executable": VVP_EXECUTABLE,
        "iverilog_available": (
            iverilog_available()
        ),
        "vvp_available": vvp_available(),
        "simulation_timeout_seconds": (
            SIMULATION_TIMEOUT_SECONDS
        ),
        "runtime_root": str(RUNTIME_ROOT),
        "run_root": str(RUN_ROOT),
        "log_root": str(LOG_ROOT),
    }


# ============================================================================
# Backward Compatibility
# ============================================================================

# Some earlier project versions used these names.

APP_TITLE = APP_NAME

MODEL_NAME = GROQ_MODEL

TEMPERATURE = LLM_TEMPERATURE

MAX_TOKENS = LLM_MAX_TOKENS

MAX_ITERATION = DEFAULT_MAX_ITERATIONS

SIM_TIMEOUT = SIMULATION_TIMEOUT_SECONDS


# ============================================================================
# Initialization
# ============================================================================

# Create runtime directories when the module is imported.
#
# This is intentionally lightweight and safe for Streamlit Cloud.

ensure_directories()


# ============================================================================
# Optional startup validation
# ============================================================================

SETTINGS_ERRORS = validate_settings()

if SETTINGS_ERRORS:
    # Do not raise an exception here.
    #
    # Raising during import would make the Streamlit application fail
    # before it can display a useful error message.
    #
    # Agents / application code may inspect SETTINGS_ERRORS when needed.
    pass

