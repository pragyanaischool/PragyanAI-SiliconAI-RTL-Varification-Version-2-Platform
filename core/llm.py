"""Optional Groq LLM adapter with deterministic demo fallback."""

from __future__ import annotations

import json
from config.settings import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, DEMO_MODE

def get_llm():
    if DEMO_MODE or not GROQ_API_KEY:
        return None
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=GROQ_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        api_key=GROQ_API_KEY,
    )

def invoke_text(system: str, user: str, fallback: str = "") -> str:
    llm = get_llm()
    if llm is None:
        return fallback
    response = llm.invoke([
        ("system", system),
        ("human", user),
    ])
    return getattr(response, "content", str(response))

def invoke_json(system: str, user: str, fallback: dict) -> dict:
    raw = invoke_text(
        system + "\nReturn ONLY valid JSON. No markdown fences.",
        user,
        json.dumps(fallback),
    )
    try:
        return json.loads(raw)
    except Exception:
        return fallback
