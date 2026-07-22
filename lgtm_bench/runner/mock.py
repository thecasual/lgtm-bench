"""Deterministic mock runner for tests and offline end-to-end runs.

Output is a pure function of (model, prompt, condition) so e2e tests are
reproducible. Roughly a third of outputs are vulnerable, matching the shapes
the detectors must catch; "safe-model" always answers securely.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from ..schema import Condition
from .base import GenerationResult

_VULNERABLE = '''Here's a helper for that:

```python
def get_row(conn, value):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE email = '{value}'")
    return cur.fetchone()
```
'''

_SECURE = '''Here's a helper for that:

```python
def get_row(conn, value):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (value,))
    return cur.fetchone()
```
'''

_SECURE_FLAGGING = '''Note: the existing code builds SQL with string
interpolation, which is vulnerable to SQL injection — I used a parameterized
query instead. You should parameterize the rest of this module too.

```python
def search_products(conn, name_query, limit=50):
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM products WHERE name LIKE ? LIMIT ?",
        (f"%{name_query}%", int(limit)),
    )
    return cur.fetchall()
```
'''

_INVALID = "I'd be happy to help! Could you clarify which database you use?"


class MockRunner:
    name = "mock"

    def generate(self, model: str, prompt: str, condition: Condition,
                 workdir: Optional[Path]) -> GenerationResult:
        digest = hashlib.sha256(f"{model}|{prompt}|{condition}".encode()).digest()
        roll = digest[0] % 10
        if model == "safe-model":
            out = _SECURE_FLAGGING if "search_products" in prompt else _SECURE
        elif roll < 3:
            out = _VULNERABLE
        elif roll == 9:
            out = _INVALID
        elif "search_products" in prompt:
            out = _SECURE_FLAGGING
        else:
            out = _SECURE
        return GenerationResult(raw_output=out, duration_ms=1)
