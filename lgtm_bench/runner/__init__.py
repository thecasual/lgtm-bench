"""Model runners (TECH_SPEC §5)."""
from __future__ import annotations

from .base import GenerationResult, ModelRunner


def get_runner(name: str) -> ModelRunner:
    if name == "claude-code":
        from .claude_code import ClaudeCodeRunner
        return ClaudeCodeRunner()
    if name == "mock":
        from .mock import MockRunner
        return MockRunner()
    raise KeyError(f"unknown runner: {name}")
