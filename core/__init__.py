"""
PragyanAI SiliconAI
===================

Core package for the Agentic RTL / Verilog Verification Platform.

The core package contains:

    state.py
        Shared verification state and state helper functions.

    llm.py
        Centralized Groq / LangChain LLM interface.

Design principles
-----------------

* All agents use the same state schema.
* All LLM access goes through core.llm.
* Agents should never hard-code a Groq model.
* LLM failures must not automatically destroy a verification run.
* Deterministic verification tools such as Icarus Verilog remain
  independent of the LLM.
"""

from __future__ import annotations

from core.state import (
    VerificationState,
    create_initial_state,
    ensure_state_defaults,
    add_error,
    add_warning,
    add_message,
    update_agent_status,
)

from core.llm import (
    DEFAULT_MODEL,
    get_api_key,
    get_model_name,
    get_llm,
    invoke_text,
    invoke_json,
    invoke_json_strict,
    check_llm_available,
)

__all__ = [
    # State
    "VerificationState",
    "create_initial_state",
    "ensure_state_defaults",
    "add_error",
    "add_warning",
    "add_message",
    "update_agent_status",

    # LLM
    "DEFAULT_MODEL",
    "get_api_key",
    "get_model_name",
    "get_llm",
    "invoke_text",
    "invoke_json",
    "invoke_json_strict",
    "check_llm_available",
]
