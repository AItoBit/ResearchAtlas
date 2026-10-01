"""Interchangeable model adapters. Calibration uses a heuristic adapter (no API)."""

from __future__ import annotations

from typing import Any, Protocol


class ModelAdapter(Protocol):
    name: str

    def generate(self, prompt: str, **kwargs: Any) -> str: ...


class HeuristicAdapter:
    """Deterministic stand-in so the sequential worker needs no paid model calls."""

    name = "heuristic"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[heuristic adapter; no model call] {prompt[:200]}"


class OpenAIAdapter:
    """Placeholder for a later provider. Refuses to run without an explicit key."""

    name = "openai"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        raise RuntimeError("OpenAI adapter is not enabled in the MVP (max_model_calls=0).")
