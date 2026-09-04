"""
PragyanAI SiliconAI
===================

Centralized LLM interface.

All agents that require an LLM should use this module.

Do NOT instantiate ChatGroq directly inside individual agents.

Supported operations
--------------------

    get_llm()
    invoke_text()
    invoke_json()
    invoke_json_strict()
    call_llm()
    check_llm_available()

Design principles
-----------------

* Groq model is centrally configured.
* Streamlit Secrets are supported through config.settings and st.secrets.
* Environment variables are supported.
* LLM failures are captured instead of crashing the entire workflow.
* JSON responses are normalized.
* Markdown fences around JSON are removed.
* Deterministic verification does not depend on this module.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Optional LangChain import
# ---------------------------------------------------------------------------

try:
    from langchain_groq import ChatGroq

    LANGCHAIN_GROQ_AVAILABLE = True

except Exception:
    ChatGroq = None
    LANGCHAIN_GROQ_AVAILABLE = False


# ---------------------------------------------------------------------------
# Configuration & Secrets Resolution
# ---------------------------------------------------------------------------

def _streamlit_secret(
    name: str,
) -> str:
    """
    Read a Streamlit secret safely without making Streamlit mandatory.
    """
    try:
        import streamlit as st

        if (
            hasattr(st, "secrets")
            and st.secrets
            and name in st.secrets
        ):
            value = st.secrets[name]

            if value is not None:
                return str(value).strip()

    except Exception:
        pass

    return ""


def get_api_key() -> str:
    """
    Resolve Groq API key.

    Priority:
        1. Environment variables
        2. Streamlit secrets (`st.secrets`)
        3. settings.py fallback
    """
    value = os.getenv(
        "GROQ_API_KEY",
        "",
    ).strip()

    if value:
        return value

    value = _streamlit_secret(
        "GROQ_API_KEY"
    )

    if value:
        return value

    return str(
        GROQ_API_KEY or ""
    ).strip()


def get_model_name() -> str:
    """
    Resolve Groq model name.

    Priority:
        1. Environment variables
        2. Streamlit secrets (`st.secrets`)
        3. settings.py fallback
        4. Default model
    """
    value = os.getenv(
        "GROQ_MODEL",
        "",
    ).strip()

    if value:
        return value

    value = _streamlit_secret(
        "GROQ_MODEL"
    )

    if value:
        return value

    value = str(
        GROQ_MODEL or ""
    ).strip()

    if value:
        return value

    return DEFAULT_MODEL


# ---------------------------------------------------------------------------
# LLM construction
# ---------------------------------------------------------------------------

def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """
    Construct the configured ChatGroq client.

    Raises a RuntimeError when LangChain-Groq is unavailable or the
    API key is missing.
    """
    if not LANGCHAIN_GROQ_AVAILABLE:
        raise RuntimeError(
            "langchain-groq is not installed. "
            "Install it with: pip install langchain-groq"
        )

    api_key = get_api_key()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured in environment variables or Streamlit secrets."
        )

    selected_model = (
        str(model).strip()
        if model
        else get_model_name()
    )

    if not selected_model:
        selected_model = DEFAULT_MODEL

    selected_temperature = (
        float(temperature)
        if temperature is not None
        else float(LLM_TEMPERATURE)
    )

    selected_max_tokens = (
        int(max_tokens)
        if max_tokens is not None
        else int(LLM_MAX_TOKENS)
    )

    return ChatGroq(
        api_key=api_key,
        model=selected_model,
        temperature=selected_temperature,
        max_tokens=selected_max_tokens,
    )


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------

def _response_to_text(
    response: Any,
) -> str:
    """
    Convert a LangChain response into plain text.
    """
    if response is None:
        return ""

    if isinstance(
        response,
        str,
    ):
        return response.strip()

    content = getattr(
        response,
        "content",
        None,
    )

    if content is None:
        return str(
            response
        ).strip()

    if isinstance(
        content,
        str,
    ):
        return content.strip()

    if isinstance(
        content,
        list,
    ):
        parts: list[str] = []

        for item in content:

            if isinstance(
                item,
                str,
            ):
                parts.append(item)

            elif isinstance(
                item,
                dict,
            ):
                text = item.get(
                    "text"
                )

                if text:
                    parts.append(
                        str(text)
                    )

        return "\n".join(
            parts
        ).strip()

    return str(
        content
    ).strip()


# ---------------------------------------------------------------------------
# JSON cleanup
# ---------------------------------------------------------------------------

def _strip_code_fences(
    text: str,
) -> str:
    """
    Remove markdown code fences.
    """
    value = str(
        text or ""
    ).strip()

    if value.startswith(
        "```"
    ):
        value = re.sub(
            r"^```(?:json|JSON)?\s*",
            "",
            value,
        )

        value = re.sub(
            r"\s*```$",
            "",
            value,
        )

    return value.strip()


def _extract_json_object(
    text: str,
) -> str:
    """
    Extract the first balanced JSON object.
    """
    value = _strip_code_fences(
        text
    )

    if (
        value.startswith("{")
        and value.endswith("}")
    ):
        return value

    start = value.find(
        "{"
    )

    if start < 0:
        return value

    depth = 0
    in_string = False
    escaped = False

    for index in range(
        start,
        len(value),
    ):

        char = value[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return value[
                    start:index + 1
                ]

    return value


# ---------------------------------------------------------------------------
# Simple prompt invocation helper (`call_llm`)
# ---------------------------------------------------------------------------

def call_llm(prompt: str) -> str:
    """
    Simple wrapper to invoke the LLM with a single prompt string
    and return the text response.
    """
    return invoke_text(
        system_prompt="You are an expert Silicon RTL Verification assistant.",
        user_prompt=prompt,
        fallback="Unable to generate response at this time.",
    )


# ---------------------------------------------------------------------------
# Text invocation
# ---------------------------------------------------------------------------

def invoke_text(
    system_prompt: str,
    user_prompt: str,
    *,
    fallback: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """
    Invoke the LLM and return text.
    """
    system_text = str(
        system_prompt or ""
    ).strip()

    user_text = str(
        user_prompt or ""
    ).strip()

    try:

        llm = get_llm(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        messages = [
            (
                "system",
                system_text,
            ),
            (
                "human",
                user_text,
            ),
        ]

        response = llm.invoke(
            messages
        )

        text = _response_to_text(
            response
        )

        if text:
            return text

        return str(
            fallback or ""
        )

    except Exception:
        return str(
            fallback or ""
        )


# ---------------------------------------------------------------------------
# JSON invocation
# ---------------------------------------------------------------------------

def invoke_json(
    system_prompt: str,
    user_prompt: str,
    *,
    fallback: dict[str, Any] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Invoke the LLM and parse a JSON object.
    """
    fallback_value: dict[str, Any] = dict(
        fallback or {}
    )

    raw = invoke_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback="",
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )

    if not raw.strip():
        return fallback_value

    cleaned = _extract_json_object(
        raw
    )

    try:

        parsed = json.loads(
            cleaned
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

        return fallback_value

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        return fallback_value


# ---------------------------------------------------------------------------
# Strict JSON invocation
# ---------------------------------------------------------------------------

def invoke_json_strict(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Strict JSON invocation. Raises when valid JSON cannot be parsed.
    """
    if not get_api_key():
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    llm = get_llm(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response = llm.invoke(
        [
            (
                "system",
                str(
                    system_prompt or ""
                ).strip(),
            ),
            (
                "human",
                str(
                    user_prompt or ""
                ).strip(),
            ),
        ]
    )

    raw = _response_to_text(
        response
    )

    if not raw:
        raise ValueError(
            "LLM returned an empty response."
        )

    cleaned = _extract_json_object(
        raw
    )

    try:

        parsed = json.loads(
            cleaned
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            "LLM returned invalid JSON."
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise ValueError(
            "LLM JSON response must be an object."
        )

    return parsed


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def check_llm_available() -> dict[str, Any]:
    """
    Perform a lightweight LLM availability check.
    """
    model = get_model_name()
    api_key = get_api_key()

    result = {
        "available": False,
        "configured": bool(api_key),
        "langchain_groq_available": (
            LANGCHAIN_GROQ_AVAILABLE
        ),
        "model": model,
        "error": "",
    }

    if not api_key:
        result["error"] = (
            "GROQ_API_KEY is not configured."
        )

        return result

    if not LANGCHAIN_GROQ_AVAILABLE:
        result["error"] = (
            "langchain-groq is not installed."
        )

        return result

    try:

        llm = get_llm(
            model=model,
            temperature=0.0,
            max_tokens=32,
        )

        response = llm.invoke(
            [
                (
                    "system",
                    "You are a connectivity test.",
                ),
                (
                    "human",
                    "Reply with exactly: OK",
                ),
            ]
        )

        text = _response_to_text(
            response
        )

        if text:
            result["available"] = True
            result["response"] = text

        else:
            result["error"] = (
                "LLM returned an empty response."
            )

    except Exception as exc:

        result["error"] = str(
            exc
        )

    return result


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def llm_config_summary() -> dict[str, Any]:
    """
    Return safe LLM configuration information.
    """
    return {
        "model": get_model_name(),
        "api_key_configured": bool(
            get_api_key()
        ),
        "langchain_groq_available": (
            LANGCHAIN_GROQ_AVAILABLE
        ),
        "temperature": float(
            LLM_TEMPERATURE
        ),
        "max_tokens": int(
            LLM_MAX_TOKENS
        ),
    }


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_MODEL",
    "LANGCHAIN_GROQ_AVAILABLE",
    "get_api_key",
    "get_model_name",
    "get_llm",
    "invoke_text",
    "invoke_json",
    "invoke_json_strict",
    "call_llm",
    "check_llm_available",
    "llm_config_summary",
]
