"""Thin OpenAI-compatible client for the LLM planner.

Reads NUCLEIPILOT_API_BASE / API_KEY / MODEL from the repo's .env (via
python-dotenv). Works with OpenRouter, OpenAI, Anthropic, or local Ollama.
`chat_json` returns (parsed_json | None, raw_text, usage | None, error | None)
and NEVER raises -- an API/parse failure is returned as data so the planner can
record it and stop safely instead of crashing.
"""
from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO, ".env"))


def _extract_json(text: str):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


class LLMClient:
    def __init__(self, api_base=None, api_key=None, model=None,
                 temperature: float = 0.0, timeout: int = 30):
        self.api_base = api_base or os.getenv("NUCLEIPILOT_API_BASE")
        self.api_key = api_key or os.getenv("NUCLEIPILOT_API_KEY")
        self.model = model or os.getenv("NUCLEIPILOT_MODEL")
        self.temperature = temperature
        self.timeout = timeout
        from openai import OpenAI
        self._client = OpenAI(
            base_url=self.api_base, api_key=self.api_key, timeout=timeout,
            default_headers={"HTTP-Referer": "http://localhost/nucleipilot",
                             "X-Title": "NucleiPilot"},
        )

    def chat_json(self, system: str, user: str):
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        try:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=self.temperature,
                    response_format={"type": "json_object"})
            except Exception:
                # some models/endpoints reject response_format -> retry without
                resp = self._client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=self.temperature)
            text = resp.choices[0].message.content or ""
            u = getattr(resp, "usage", None)
            usage = ({"prompt_tokens": getattr(u, "prompt_tokens", None),
                      "completion_tokens": getattr(u, "completion_tokens", None)}
                     if u else None)
            parsed = _extract_json(text)
            if parsed is None:
                return None, text, usage, "could not parse JSON from model output"
            return parsed, text, usage, None
        except Exception as e:
            return None, "", None, f"{type(e).__name__}: {e}"
