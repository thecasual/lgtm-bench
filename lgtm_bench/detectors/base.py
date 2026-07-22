"""Detector protocol."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schema import Finding, TaskSpec


@runtime_checkable
class Detector(Protocol):
    name: str

    def scan(self, code: str, task: TaskSpec) -> list[Finding]:
        """Grade one trial's extracted code for this detector's category."""
        ...
