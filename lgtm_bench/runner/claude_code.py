"""Claude Code headless runner (TECH_SPEC §5.2).

All usage rides the local `claude` CLI login (subscription) — no API key.
- condition `none`: empty scratch cwd, all tools disabled → pure generation.
- repo conditions: cwd is a fresh fixture copy, read-only tools enabled.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..schema import Condition
from .base import GenerationResult

# Session-identity vars are stripped so concurrent trials don't collide with
# the parent session; CLAUDE_EFFORT is stripped so trials measure the
# product-default configuration.
_STRIP_ENV = {"CLAUDE_CODE_SESSION_ID", "CLAUDE_EFFORT", "CLAUDE_CODE_CHILD_SESSION"}

_RATE_LIMIT_MARKERS = ("rate limit", "rate_limit", "overloaded", "429", "529")


class ClaudeCodeRunner:
    name = "claude-code"

    def __init__(self, binary: str = "claude", timeout_s: int = 300,
                 max_retries: int = 4):
        self.binary = binary
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def _env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k not in _STRIP_ENV}
        return env

    def _cmd(self, model: str, prompt: str, condition: Condition) -> list[str]:
        cmd = [self.binary, "-p", prompt, "--model", model, "--output-format", "json"]
        if condition == Condition.NONE:
            cmd += ["--disallowedTools", "*"]
        else:
            cmd += ["--allowedTools", "Read,Glob,Grep"]
        return cmd

    def generate(self, model: str, prompt: str, condition: Condition,
                 workdir: Optional[Path]) -> GenerationResult:
        assert workdir is not None, "claude-code runner requires a scratch workdir"
        cmd = self._cmd(model, prompt, condition)
        last_err = "unknown"
        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                proc = subprocess.run(
                    cmd, cwd=workdir, env=self._env(), capture_output=True,
                    text=True, timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                last_err = f"timeout after {self.timeout_s}s"
                continue  # a timeout is retried like an error
            elapsed_ms = int((time.monotonic() - start) * 1000)
            payload = None
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                pass
            if payload is not None and not payload.get("is_error") and \
                    isinstance(payload.get("result"), str):
                meta = {
                    "cli_session_id": payload.get("session_id"),
                    "num_turns": payload.get("num_turns"),
                    "stop_reason": payload.get("stop_reason"),
                }
                return GenerationResult(raw_output=payload["result"],
                                        duration_ms=elapsed_ms, meta=meta)
            blob = (proc.stdout or "") + (proc.stderr or "")
            last_err = (blob.strip() or f"exit={proc.returncode}")[:500]
            lowered = blob.lower()
            transient = proc.returncode != 0 or payload is None or \
                any(m in lowered for m in _RATE_LIMIT_MARKERS)
            if not transient:
                break
            if attempt < self.max_retries:
                delay = (5 * 2 ** attempt) + random.uniform(0, 3)
                time.sleep(delay)
        return GenerationResult(raw_output="", duration_ms=0, error=last_err)


def cli_version(binary: str = "claude") -> str:
    try:
        out = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, timeout=30)
        return out.stdout.strip().splitlines()[0] if out.stdout else "unknown"
    except Exception:
        return "unavailable"
