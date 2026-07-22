"""Ollama HTTP runner (open-source models served by an Ollama host).

Lets OSS models (llama3.2, qwen3, ...) served by a remote Ollama daemon be
benchmarked alongside the Claude models. Ollama is a raw model API with no
filesystem or tool access, so only condition `none` (pure generation) is
supported; repo conditions return an honest error rather than a silently
wrong result.

Host is read from ``INFERENCE_HOST`` (env or a ``.env`` line at the repo
root). Talks to the documented Ollama HTTP API using only the standard
library — no third-party HTTP dependency.

    POST <base>/api/generate
    {"model": ..., "prompt": ..., "stream": false, "options": {"temperature": ...}}

See https://github.com/ollama/ollama/blob/main/docs/api.md
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from ..schema import Condition
from .base import GenerationResult

DEFAULT_PORT = 11434
DEFAULT_SCHEME = "http"

_REPO_CONDITION_ERROR = (
    "ollama runner: repo conditions not supported (no tool access); "
    "run condition=none"
)

# Deterministic backoff jitter — a fixed sequence rather than random(), so
# retry timing is reproducible under test.
_JITTER_SEQUENCE = (0.3, 0.7, 0.1, 0.5, 0.9)


def _repo_root() -> Path:
    # .../lgtm_bench/runner/ollama.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def resolve_base_url(raw: str) -> str:
    """Turn a host spec into an Ollama base URL ``http://<host>:<port>``.

    Accepts, in order of precedence:
      * a full ``http://`` / ``https://`` URL       -> scheme+netloc preserved
      * an ssh-style ``user@host`` convenience      -> the ``user@`` is stripped
      * ``host:port``                               -> used as given
      * bare ``host``                               -> default port appended

    Default port is 11434, default scheme http.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty INFERENCE_HOST")

    # Full URL: preserve scheme + host[:port], drop any trailing path/slash so
    # callers can safely append "/api/generate".
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        if not parsed.netloc:
            raise ValueError(f"malformed INFERENCE_HOST url: {raw!r}")
        return f"{parsed.scheme}://{parsed.netloc}"

    # ssh-style "user@host": the user@ is a convenience, strip it.
    if "@" in raw:
        raw = raw.rsplit("@", 1)[1]

    # host or host:port
    if ":" in raw:
        host, _, port = raw.partition(":")
        if not host or not port:
            raise ValueError(f"malformed INFERENCE_HOST host:port: {raw!r}")
        netloc = f"{host}:{port}"
    else:
        netloc = f"{raw}:{DEFAULT_PORT}"

    return f"{DEFAULT_SCHEME}://{netloc}"


class OllamaRunner:
    name = "ollama"

    def __init__(self, host: Optional[str] = None, temperature: float = 0.0,
                 timeout_s: int = 300, max_retries: int = 4,
                 base_delay: float = 2.0, max_tokens: Optional[int] = None,
                 no_think: bool = False):
        self.host = host
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.base_delay = base_delay
        # Speed knobs. max_tokens caps generation (num_predict); no_think turns
        # off a reasoning model's <think> block (Ollama `think: false`). Both
        # cut a lot of wasted tokens on models like qwen3 for these tasks.
        self.max_tokens = max_tokens
        self.no_think = no_think

    def _raw_host(self) -> Optional[str]:
        """Resolve the raw host spec from ctor / env / .env, or None."""
        if self.host:
            return self.host
        import os
        val = os.environ.get("INFERENCE_HOST")
        if val and val.strip():
            return val.strip()
        env_path = _repo_root() / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() == "INFERENCE_HOST" and value.strip():
                    return value.strip()
        return None

    def _backoff(self, attempt: int) -> float:
        jitter = _JITTER_SEQUENCE[attempt % len(_JITTER_SEQUENCE)]
        return self.base_delay * (2 ** attempt) + jitter

    def _request(self, url: str, body: dict) -> dict:
        """POST JSON and return the parsed single-object response.

        Isolated so tests can monkeypatch the HTTP boundary. Raises
        urllib.error.URLError / OSError on transport failure.
        """
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def generate(self, model: str, prompt: str, condition: Condition,
                 workdir: Optional[Path]) -> GenerationResult:
        if condition != Condition.NONE:
            return GenerationResult(raw_output="", duration_ms=0,
                                    error=_REPO_CONDITION_ERROR)

        raw_host = self._raw_host()
        if not raw_host:
            return GenerationResult(
                raw_output="", duration_ms=0,
                error="ollama runner: no INFERENCE_HOST set (env or repo .env)")
        try:
            base_url = resolve_base_url(raw_host)
        except ValueError as e:
            return GenerationResult(raw_output="", duration_ms=0,
                                    error=f"ollama runner: {e}")
        url = base_url + "/api/generate"
        options = {"temperature": self.temperature}
        if self.max_tokens is not None:
            options["num_predict"] = self.max_tokens
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if self.no_think:
            # Ollama passes this to thinking-capable models (qwen3, etc.) to
            # suppress the reasoning block. Ignored by models without it.
            body["think"] = False

        last_err = "unknown"
        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                data = self._request(url, body)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = f"ollama request to {url} failed: {e}"[:500]
                if attempt < self.max_retries:
                    time.sleep(self._backoff(attempt))
                    continue
                break
            except json.JSONDecodeError as e:
                last_err = f"ollama: could not parse response JSON: {e}"[:500]
                break  # a malformed body is not a transient transport error

            elapsed_ms = int((time.monotonic() - start) * 1000)
            response_text = data.get("response")
            if not isinstance(response_text, str):
                last_err = f"ollama: response field missing/not a string: {data!r}"[:500]
                break
            meta = {
                "model": data.get("model"),
                "done_reason": data.get("done_reason"),
                "total_duration_ns": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "base_url": base_url,
            }
            return GenerationResult(raw_output=response_text,
                                    duration_ms=elapsed_ms, meta=meta)

        return GenerationResult(raw_output="", duration_ms=0, error=last_err)
