"""
PragyanAI SiliconAI
===================

Observability package for the Agentic RTL / Verilog Verification
Platform.

This package provides run-level logging, activity tracking,
artifact management, and verification-run lifecycle management.

Public API
----------

    ActivityLogger
        Structured logging and artifact management for one run.

    VerificationRun
        Container representing one verification run.

    create_run_id()
        Generate a unique verification run identifier.

    create_verification_run()
        Create one verification run and one shared logger.

    finalize_verification_run()
        Finalize a verification run.

    finalize_from_state()
        Finalize a run from LangGraph workflow state.

Utility functions
-----------------

    utc_now()
        Return the current UTC timestamp.

    safe_filename()
        Convert text into a filesystem-safe filename.

    safe_json_value()
        Convert Python values into JSON-compatible values.

    sha256_file()
        Compute the SHA256 hash of a file safely.
"""

from __future__ import annotations


# ============================================================================
# Activity Logger
# ============================================================================

from observability.activity_logger import (
    ActivityLogger,
    safe_filename,
    safe_json_value,
    sha256_file,
    utc_now,
)


# ============================================================================
# Run Manager
# ============================================================================

from observability.run_manager import (
    VerificationRun,
    create_run_id,
    create_verification_run,
    finalize_from_state,
    finalize_verification_run,
)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Activity logging
    "ActivityLogger",

    # Run management
    "VerificationRun",
    "create_run_id",
    "create_verification_run",
    "finalize_verification_run",
    "finalize_from_state",

    # Utilities
    "utc_now",
    "safe_filename",
    "safe_json_value",
    "sha256_file",
]

