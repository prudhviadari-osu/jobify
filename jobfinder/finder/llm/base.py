"""The model-client interface + shared JSON helpers."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod


class ModelError(Exception):
    """Raised when the model is unreachable or returns unusable output."""


class ModelClient(ABC):
    @abstractmethod
    def generate_json(self, system: str, user: str, temperature: float = 0.2) -> dict | list:
        """Send a prompt expecting JSON back; return the parsed object.
        Must raise ModelError on transport failure or unparseable output."""
        raise NotImplementedError

    @abstractmethod
    def available(self) -> bool:
        """True if the backend is reachable (used for a friendly pre-check)."""
        raise NotImplementedError


_JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str) -> dict | list:
    """Pull the first JSON object/array out of a model response.

    Small local models sometimes wrap JSON in prose or ```json fences or add a
    <think> preamble. We strip those and parse the first balanced block.
    """
    if not text:
        raise ModelError("empty model response")

    # Drop <think>...</think> reasoning blocks some models emit.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip code fences.
    text = text.replace("```json", "").replace("```", "")

    # Fast path: whole thing is JSON.
    try:
        return json.loads(text.strip())
    except ValueError:
        pass

    m = _JSON_BLOCK.search(text)
    if not m:
        raise ModelError(f"no JSON found in model output: {text[:200]!r}")
    try:
        return json.loads(m.group(0))
    except ValueError as exc:
        raise ModelError(f"invalid JSON in model output: {exc}") from exc
