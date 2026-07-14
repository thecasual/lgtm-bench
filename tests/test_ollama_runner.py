"""Unit tests for the Ollama runner (stdlib + pytest + monkeypatch only).

The Ollama host lives on a Tailscale network and is unreachable from CI, so
every test that touches the network monkeypatches the HTTP boundary
(``OllamaRunner._request``) — no real request is ever made.
"""
from __future__ import annotations

import urllib.error

import pytest

from lgtm_bench.runner import get_runner
from lgtm_bench.runner.base import GenerationResult
from lgtm_bench.runner.ollama import OllamaRunner, resolve_base_url
from lgtm_bench.schema import Condition


# --------------------------------------------------------------------------
# resolve_base_url (pure)
# --------------------------------------------------------------------------

def test_resolve_ssh_style_strips_user_and_adds_default_port():
    assert resolve_base_url("sam@server.taild0cb05.ts.net") == \
        "http://server.taild0cb05.ts.net:11434"


def test_resolve_host_with_explicit_port():
    assert resolve_base_url("host:9999") == "http://host:9999"


def test_resolve_full_https_url_scheme_preserved():
    assert resolve_base_url("https://x/") == "https://x"


def test_resolve_bare_host_gets_default_port():
    assert resolve_base_url("host") == "http://host:11434"


def test_resolve_empty_raises():
    with pytest.raises(ValueError):
        resolve_base_url("  ")


# --------------------------------------------------------------------------
# generate: happy path
# --------------------------------------------------------------------------

_FAKE_RESPONSE = "```python\ndef f(): ...\n```"


def test_generate_happy_path(monkeypatch):
    monkeypatch.setenv("INFERENCE_HOST", "host:11434")
    runner = OllamaRunner()

    captured = {}

    def fake_request(self, url, body):
        captured["url"] = url
        captured["body"] = body
        return {"model": "llama3.2:3b", "response": _FAKE_RESPONSE,
                "done_reason": "stop", "eval_count": 7}

    monkeypatch.setattr(OllamaRunner, "_request", fake_request)

    result = runner.generate("llama3.2:3b", "write f", Condition.NONE, None)

    assert isinstance(result, GenerationResult)
    assert result.error is None
    assert result.raw_output == _FAKE_RESPONSE
    # correct endpoint + request body shape
    assert captured["url"] == "http://host:11434/api/generate"
    assert captured["body"]["model"] == "llama3.2:3b"
    assert captured["body"]["prompt"] == "write f"
    assert captured["body"]["stream"] is False
    assert "temperature" in captured["body"]["options"]
    assert result.meta["eval_count"] == 7


# --------------------------------------------------------------------------
# generate: connection failure -> retries then error, never raises
# --------------------------------------------------------------------------

def test_generate_connection_failure_retries_then_errors(monkeypatch):
    monkeypatch.setenv("INFERENCE_HOST", "host:11434")
    # no real sleeping between retries
    monkeypatch.setattr("lgtm_bench.runner.ollama.time.sleep", lambda *_: None)

    calls = {"n": 0}

    def boom(self, url, body):
        calls["n"] += 1
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(OllamaRunner, "_request", boom)

    runner = OllamaRunner(max_retries=3)
    result = runner.generate("llama3.2:3b", "hi", Condition.NONE, None)

    assert isinstance(result, GenerationResult)
    assert result.raw_output == ""
    assert result.error is not None
    assert "connection refused" in result.error
    # initial attempt + 3 retries
    assert calls["n"] == 4


# --------------------------------------------------------------------------
# generate: repo conditions unsupported
# --------------------------------------------------------------------------

@pytest.mark.parametrize("condition", [Condition.CLEAN, Condition.DIRTY])
def test_generate_repo_condition_unsupported(condition, monkeypatch):
    monkeypatch.setenv("INFERENCE_HOST", "host:11434")

    def should_not_be_called(self, url, body):  # pragma: no cover
        raise AssertionError("HTTP must not be attempted for repo conditions")

    monkeypatch.setattr(OllamaRunner, "_request", should_not_be_called)

    result = OllamaRunner().generate("m", "p", condition, None)
    assert result.raw_output == ""
    assert result.error == (
        "ollama runner: repo conditions not supported (no tool access); "
        "run condition=none")


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

def test_get_runner_returns_ollama_runner():
    runner = get_runner("ollama")
    assert isinstance(runner, OllamaRunner)
    assert runner.name == "ollama"
