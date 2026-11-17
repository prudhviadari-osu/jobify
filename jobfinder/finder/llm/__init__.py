"""Local-LLM layer for Phase 2 (scoring, advising, keyword expansion).

The rest of the code talks to a `ModelClient` interface, so the backend is
swappable (DESIGN.md §6.6): Ollama locally by default, a deterministic fake for
offline tests.
"""
from .base import ModelClient, ModelError
from .ollama_client import OllamaClient
from .fake_client import FakeClient

__all__ = ["ModelClient", "ModelError", "OllamaClient", "FakeClient", "get_client"]


def get_client(config):
    """Factory: pick a backend from config.LLM_BACKEND ('ollama' | 'fake')."""
    backend = getattr(config, "LLM_BACKEND", "ollama")
    if backend == "fake":
        return FakeClient()
    return OllamaClient(
        host=getattr(config, "OLLAMA_HOST", "http://localhost:11434"),
        model=getattr(config, "OLLAMA_MODEL", "qwen3:8b"),
    )
