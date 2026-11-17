"""Ollama backend — talks to a local Ollama server (free, offline).

Setup on your machine (one time):
    1. Install Ollama:  https://ollama.com/download
    2. Pull the model:  ollama pull qwen3:8b        (or phi4-mini for low RAM)
    3. Ollama serves on http://localhost:11434 automatically.

Nothing leaves your machine; no API key.
"""
from __future__ import annotations

import json

import requests

from .base import ModelClient, ModelError, extract_json


class OllamaClient(ModelClient):
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3:8b",
                 timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def available(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=4)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def generate_json(self, system: str, user: str, temperature: float = 0.2) -> dict | list:
        payload = {
            "model": self.model,
            "prompt": user,
            "system": system,
            "stream": False,
            "format": "json",          # ask Ollama to constrain output to JSON
            "options": {"temperature": temperature},
        }
        try:
            r = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
            r.raise_for_status()
            body = r.json()
        except requests.RequestException as exc:
            raise ModelError(
                f"Ollama not reachable at {self.host} ({exc}). Is it running? "
                f"Try: ollama pull {self.model}"
            ) from exc
        except ValueError as exc:
            raise ModelError(f"Ollama returned non-JSON envelope: {exc}") from exc

        return extract_json(body.get("response", ""))
