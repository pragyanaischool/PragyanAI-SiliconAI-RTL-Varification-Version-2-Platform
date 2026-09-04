"""
PragyanAI SiliconAI
===================

Central LLM interface for the Agentic RTL Verification Platform.

Responsibilities
----------------
- Create the Groq Chat model from central settings.
- Never hard-code an agent-specific model.
- Use GROQ_MODEL from config.settings.
- Provide text generation.
- Provide JSON generation.
- Gracefully handle missing API keys.
- Provide deterministic fallbacks when LLM is unavailable.
- Keep LLM behavior centralized so every agent uses the same configuration.

Supported backend
-----------------
Groq + LangChain

Default model
-------------
openai/gpt-oss-120b

SymbiYosys is NOT required.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


# ============================================================================
# OPTIONAL LANGCHAIN / GROQ IMPORT
# ============================================================================

try:
    from langchain_groq import ChatGroq

    LANGCHAIN_GROQ_AVAILABLE = True

except Exception:
    ChatGroq = None
    LANGCHAIN_GROQ_AVAILABLE = False


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_MODEL = "openai/gpt-oss-120b"


# ============================================================================
# MODEL RESOLUTION
# ============================================================================

def get_model_name() -> str:
    """
    Return the configured Groq model.

    Priority:
        1. GROQ_MODEL environment variable
        2. config.settings.GROQ_MODEL
        3. safe default

    The application should therefore never silently use
    llama-3.3-70b-versatile unless the user explicitly configures it.
    """

    model = (
        os.getenv("GROQ_MODEL")
        or GROQ_MODEL
        or DEFAULT_MODEL
    ).strip()

    if not model:
        model = DEFAULT_MODEL

    return model


# ============================================================================
# API KEY
# ============================================================================

def get_api_key() -> str:
    """
    Return the configured Groq API key.

    Environment variables take precedence because this works
    cleanly with Streamlit Cloud secrets.
    """

    return (
        os.getenv("GROQ_API_KEY")
        or GROQ_API_KEY
        or ""
    ).strip()


# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def get_llm_config() -> Dict[str, Any]:
    """
    Return safe LLM configuration information.

    Never returns the actual API key.
    """

    api_key = get_api_key()

    return {
        "provider": "groq",
        "model": get_model_name(),
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "api_key_configured": bool(api_key),
        "langchain_groq_available": LANGCHAIN_GROQ_AVAILABLE,
    }


# ============================================================================
# MODEL FACTORY
# ============================================================================

def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
):
    """
    Create and return the central ChatGroq model.

    Parameters
    ----------
    model:
        Optional explicit model override.

    temperature:
        Optional temperature override.

    max_tokens:
        Optional completion token limit.

    Returns
    -------
    ChatGroq

    Raises
    ------
    RuntimeError
        If langchain-groq is unavailable or API key is missing.
    """

    if not LANGCHAIN_GROQ_AVAILABLE:
        raise RuntimeError(
            "langchain-groq is not installed. "
            "Add 'langchain-groq' to requirements.txt."
        )

    api_key = get_api_key()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "Add GROQ_API_KEY to Streamlit Cloud Secrets "
            "or the environment."
        )

    selected_model = (
        model
        or get_model_name()
    ).strip()

    selected_temperature = (
        LLM_TEMPERATURE
        if temperature is None
        else temperature
    )

    selected_max_tokens = (
        LLM_MAX_TOKENS
        if max_tokens is None
        else max_tokens
    )

    return ChatGroq(
        api_key=api_key,
        model=selected_model,
        temperature=selected_temperature,
        max_tokens=selected_max_tokens,
    )


# ============================================================================
# MODEL AVAILABILITY CHECK
# ============================================================================

def check_llm_available(
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform a lightweight LLM availability check.

    This is useful from Streamlit or diagnostics.

    Returns
    -------
    dict
        {
            "available": bool,
            "model": str,
            "message": str
        }
    """

    selected_model = (
        model
        or get_model_name()
    )

    if not LANGCHAIN_GROQ_AVAILABLE:
        return {
            "available": False,
            "model": selected_model,
            "message": (
                "langchain-groq is not installed."
            ),
        }

    if not get_api_key():
        return {
            "available": False,
            "model": selected_model,
            "message": (
                "GROQ_API_KEY is not configured."
            ),
        }

    try:
        llm = get_llm(
            model=selected_model,
            temperature=0.0,
            max_tokens=8,
        )

        llm.invoke(
            [
                (
                    "system",
                    "You are a verification system health checker.",
                ),
                (
                    "human",
                    "Reply with OK.",
                ),
            ]
        )

        return {
            "available": True,
            "model": selected_model,
            "message": "Groq model is available.",
        }

    except Exception as exc:
        return {
            "available": False,
            "model": selected_model,
            "message": str(exc),
        }


# ============================================================================
# TEXT EXTRACTION
# ============================================================================

def _extract_response_text(response: Any) -> str:
    """
    Extract plain text from a LangChain response.
    """

    if response is None:
        return ""

    content = getattr(
        response,
        "content",
        response,
    )

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")

                if text:
                    parts.append(str(text))

        return "\n".join(parts).strip()

    return str(content).strip()


# ============================================================================
# MARKDOWN FENCE CLEANUP
# ============================================================================

def _strip_markdown_fences(text: str) -> str:
    """
    Remove common Markdown code fences.

    Example:

        ```json
        {"a": 1}
        ```

    becomes:

        {"a": 1}
    """

    if not text:
        return ""

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json|JSON)?\s*",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    return cleaned.strip()


# ============================================================================
# JSON EXTRACTION
# ============================================================================

def _extract_json_text(text: str) -> str:
    """
    Attempt to isolate a JSON object or JSON array from model output.
    """

    cleaned = _strip_markdown_fences(text)

    if not cleaned:
        return cleaned

    # Already valid JSON.
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    # Try object.
    object_start = cleaned.find("{")
    object_end = cleaned.rfind("}")

    if (
        object_start >= 0
        and object_end > object_start
    ):
        candidate = cleaned[
            object_start:
            object_end + 1
        ]

        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    # Try array.
    array_start = cleaned.find("[")
    array_end = cleaned.rfind("]")

    if (
        array_start >= 0
        and array_end > array_start
    ):
        candidate = cleaned[
            array_start:
            array_end + 1
        ]

        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    return cleaned


# ============================================================================
# TEXT INVOCATION
# ============================================================================

def invoke_text(
    system: str,
    user: str,
    fallback: str = "",
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Invoke the configured Groq model.

    If the model is unavailable or the API fails, return fallback.

    This behavior is intentional because RTL verification should
    remain usable in deterministic/demo mode.
    """

    try:
        llm = get_llm(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response = llm.invoke(
            [
                (
                    "system",
                    system,
                ),
                (
                    "human",
                    user,
                ),
            ]
        )

        text = _extract_response_text(
            response
        )

        if text:
            return text

        return fallback

    except Exception:
        return fallback


# ============================================================================
# JSON INVOCATION
# ============================================================================

def invoke_json(
    system: str,
    user: str,
    fallback: Any,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Any:
    """
    Invoke the configured LLM and parse JSON.

    Important:
        The function does NOT allow a failed model call to crash
        the complete verification workflow.

    If the model cannot be called or returns invalid JSON,
    the supplied fallback is returned.
    """

    fallback_value = fallback

    if isinstance(fallback, str):
        try:
            fallback_value = json.loads(
                fallback
            )
        except Exception:
            fallback_value = fallback

    json_system = (
        system
        + "\n\n"
        + "Return ONLY valid JSON. "
        + "Do not use Markdown fences. "
        + "Do not include explanations outside JSON."
    )

    raw = invoke_text(
        json_system,
        user,
        "",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if not raw:
        return fallback_value

    cleaned = _extract_json_text(
        raw
    )

    try:
        return json.loads(
            cleaned
        )

    except Exception:
        return fallback_value


# ============================================================================
# STRICT JSON INVOCATION
# ============================================================================

def invoke_json_strict(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Any:
    """
    Strict version of invoke_json.

    Unlike invoke_json(), this raises an exception when
    the model call fails or invalid JSON is returned.

    Useful for diagnostics and development.
    """

    llm = get_llm(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response = llm.invoke(
        [
            (
                "system",
                system
                + "\n\n"
                + "Return ONLY valid JSON.",
            ),
            (
                "human",
                user,
            ),
        ]
    )

    raw = _extract_response_text(
        response
    )

    if not raw:
        raise ValueError(
            "LLM returned an empty response."
        )

    cleaned = _extract_json_text(
        raw
    )

    return json.loads(
        cleaned
    )


# ============================================================================
# SAFE MODEL NAME
# ============================================================================

def is_known_groq_model(model: str) -> bool:
    """
    Return whether the model is one of the known production models
    currently used by this application.

    This is intentionally conservative.

    It does NOT guarantee that the user's Groq project has permission
    to access the model.
    """

    known_models = {
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    }

    return model.strip() in known_models


# ============================================================================
# MODEL RECOMMENDATION
# ============================================================================

def recommended_model() -> str:
    """
    Return the recommended default model for this platform.
    """

    return DEFAULT_MODEL


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "get_llm",
    "get_model_name",
    "get_api_key",
    "get_llm_config",
    "check_llm_available",
    "invoke_text",
    "invoke_json",
    "invoke_json_strict",
    "is_known_groq_model",
    "recommended_model",
]

