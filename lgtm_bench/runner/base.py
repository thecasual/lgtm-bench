"""Runner protocol (TECH_SPEC §5.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from ..schema import Condition


@dataclass
class GenerationResult:
    raw_output: str
    duration_ms: int
    error: Optional[str] = None
    meta: dict = field(default_factory=dict)


class ModelRunner(Protocol):
    name: str

    def generate(self, model: str, prompt: str, condition: Condition,
                 workdir: Optional[Path]) -> GenerationResult:
        """One trial. Returns raw output text + metadata."""
        ...
