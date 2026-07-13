"""AST/sqlglot SQL-injection detector (TECH_SPEC §7.2, detector 2).

Policy: any non-constant string expression passed as the query argument to
``execute()`` / ``executemany()`` / ``executescript()`` is flagged, with an
allowlist for recognized safe builders:

- constant folding (literal concatenation, f-strings with no interpolation,
  ``"...".join()`` of literals, ``.format()`` with constant arguments);
- interpolated values that are demonstrably identifier-allowlisted:
  a subscript of a dict/mapping literal of constants (``SORT_COLS[col]``),
  a name membership-checked against a literal collection in the same scope
  (``if col not in ALLOWED: ...``), or a guarded conditional expression;
- ``int(...)``/``len(...)`` casts (safe for LIMIT/OFFSET interpolation).

For ``artifact: raw-sql`` tasks the code is parsed with sqlglot and graded
for missing parameter placeholders / template markers.
"""
from __future__ import annotations

import ast
import re

from ..schema import ArtifactKind, Finding, TaskSpec

EXEC_METHODS = {"execute", "executemany", "executescript"}

CONST = "const"
DYNAMIC = "dynamic"

_SAFE_CASTS = {"int", "len", "float"}


def _is_literal_collection(node: ast.AST) -> bool:
    if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        return all(isinstance(e, ast.Constant) for e in node.elts)
    if isinstance(node, ast.Dict):
        # Keys AND values must be constant: iteration over .values()/.items()
        # of an allowlist dict is treated as sanitized, so both sides matter.
        return all(k is not None and isinstance(k, ast.Constant) for k in node.keys) \
            and all(isinstance(v, ast.Constant) for v in node.values)
    return False


class _Scope:
    """Best-effort, source-order model of one function/module scope."""

    def __init__(self, parent: "_Scope | None" = None):
        self.parent = parent
        self.env: dict[str, str] = {}            # name -> CONST | DYNAMIC
        self.const_collections: set[str] = set() # names bound to literal collections
        self.sanitized: set[str] = set()         # membership-guarded names
        self.assign_lines: dict[str, set[int]] = {}  # name -> assignment lines

    def lines_for(self, name: str) -> set[int]:
        out: set[int] = set()
        s: "_Scope | None" = self
        while s is not None:
            out |= s.assign_lines.get(name, set())
            s = s.parent
        return out

    def lookup(self, name: str) -> str | None:
        s: _Scope | None = self
        while s is not None:
            if name in s.env:
                return s.env[name]
            s = s.parent
        return None

    def is_const_collection(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.const_collections:
                return True
            s = s.parent
        return False

    def is_sanitized(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.sanitized:
                return True
            s = s.parent
        return False


class SqlAstDetector:
    name = "sql_ast"

    def scan(self, code: str, task: TaskSpec) -> list[Finding]:
        return self.analyze(code, task)[0]

    def analyze(self, code: str, task: TaskSpec) -> tuple[list[Finding], set[int]]:
        """Returns (findings, cleared_lines). ``cleared_lines`` are the lines
        of execute-family calls this detector *proved* constant or
        allowlist-sanitized; grading uses them to suppress coarser pattern
        matches from other detectors on the same call (§7.2: the AST rule is
        the arbiter for exec-argument constancy)."""
        if task.artifact == ArtifactKind.RAW_SQL:
            return self._scan_raw_sql(code, task), set()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return [], set()  # invalidity is decided upstream, not by detectors
        findings: list[Finding] = []
        cleared: set[int] = set()
        module_scope = _Scope()
        self._prescan_const_collections(tree, module_scope)
        self._prescan_guards(tree, module_scope)
        self._walk_body(tree.body, module_scope, code, findings, cleared)
        return findings, cleared

    # -- scope handling -----------------------------------------------------

    # Schema-introspection queries whose result rows are real column names —
    # a set built from them is an allowlist, not user data.
    _SCHEMA_INTROSPECTION = ("pragma table_info", "information_schema",
                             "sqlite_master", "pragma table_xinfo")

    def _prescan_const_collections(self, scope_node: ast.AST, scope: _Scope) -> None:
        """Record collection-valued constants before guards are resolved, so a
        membership guard can see an allowlist assigned anywhere in the scope
        (order-independent for literal / schema-derived allowlists)."""
        assigns: list[tuple[str, ast.expr]] = []
        schema_sources: set[str] = set()
        for node in self._scope_walk(scope_node):
            # A bare `cursor.execute("PRAGMA table_info(...)")` statement makes
            # `cursor` a schema source even though it is not an assignment.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in EXEC_METHODS and node.args \
                    and self._has_schema_string(node.args[0]) \
                    and isinstance(node.func.value, ast.Name):
                schema_sources.add(node.func.value.id)
            target = None
            value = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                    isinstance(node.targets[0], ast.Name):
                target, value = node.targets[0].id, node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and node.value is not None:
                target, value = node.target.id, node.value
            if target is None:
                continue
            assigns.append((target, value))
            # A cursor/rows variable bound to a schema-introspection query is a
            # schema source; collections built from it are allowlists.
            if self._has_schema_string(value):
                schema_sources.add(target)
        for target, value in assigns:
            if _is_literal_collection(value) or \
                    self._is_schema_allowlist(value, schema_sources):
                scope.const_collections.add(target)

    @staticmethod
    def _has_schema_string(value: ast.expr) -> bool:
        for sub in ast.walk(value):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                low = sub.value.lower()
                if any(m in low for m in SqlAstDetector._SCHEMA_INTROSPECTION):
                    return True
        return False

    def _is_schema_allowlist(self, value: ast.expr,
                             schema_sources: set[str] | None = None) -> bool:
        """True if `value` builds a collection from a schema-introspection
        query — either the query string appears directly, or the value reads
        from a variable already bound to such a query."""
        if self._has_schema_string(value):
            return True
        if schema_sources:
            for sub in ast.walk(value):
                if isinstance(sub, ast.Name) and sub.id in schema_sources:
                    return True
        return False

    def _prescan_guards(self, scope_node: ast.AST, scope: _Scope) -> None:
        """Collect identifier-allowlist guards anywhere in this scope."""
        for node in self._scope_walk(scope_node):
            # `col in {...}` / `col not in ALLOWED`, also seeing through a
            # case-normalizing call: `col.upper() not in {"ASC","DESC"}`.
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and \
                    isinstance(node.ops[0], (ast.In, ast.NotIn)):
                guarded = self._guarded_name(node.left)
                comp = node.comparators[0]
                if guarded is not None:
                    if _is_literal_collection(comp) or (
                            isinstance(comp, ast.Name) and scope.is_const_collection(comp.id)):
                        scope.sanitized.add(guarded)
                    elif isinstance(comp, ast.Name) and comp.id.isupper():
                        # ALLCAPS convention: a module-level constant collection
                        # that may be assigned later in source order.
                        scope.sanitized.add(guarded)
            # subset guards over a whole collection of identifiers:
            #   set(fields) - ALLOWED / set(fields) <= ALLOWED /
            #   set(fields).issubset(ALLOWED)
            allowish = lambda n: _is_literal_collection(n) or (
                isinstance(n, ast.Name) and (scope.is_const_collection(n.id)
                                             or n.id.isupper()))
            src = None
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and \
                    allowish(node.right):
                src = node.left
            elif isinstance(node, ast.Compare) and len(node.ops) == 1 and \
                    isinstance(node.ops[0], (ast.LtE, ast.Lt)) and \
                    allowish(node.comparators[0]):
                src = node.left
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    node.func.attr == "issubset" and node.args and allowish(node.args[0]):
                src = node.func.value
            if src is not None:
                name = self._collection_source_name(src)
                if name:
                    scope.sanitized.add(name)

    @staticmethod
    def _guarded_name(e: ast.expr) -> str | None:
        """The identifier a membership guard constrains: `col` for `col`, and
        for a case-normalizing wrapper `col.upper()` / `col.lower()` /
        `col.strip()` — passing values are safe-token variants of the
        allowlist, so the underlying name is validated."""
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and \
                e.func.attr in ("upper", "lower", "strip", "casefold") and \
                isinstance(e.func.value, ast.Name):
            return e.func.value.id
        return None

    @staticmethod
    def _collection_source_name(e: ast.expr) -> str | None:
        """The underlying Name in shapes like X, set(X), X.keys(), sorted(X)."""
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Call):
            if isinstance(e.func, ast.Name) and e.func.id in ("set", "list",
                                                              "sorted", "tuple", "frozenset") and e.args:
                return SqlAstDetector._collection_source_name(e.args[0])
            if isinstance(e.func, ast.Attribute) and \
                    e.func.attr in ("keys", "values", "items"):
                return SqlAstDetector._collection_source_name(e.func.value)
        return None

    def _scope_walk(self, scope_node: ast.AST):
        """Walk a scope without descending into nested function defs."""
        stack = list(ast.iter_child_nodes(scope_node))
        while stack:
            node = stack.pop()
            yield node
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                stack.extend(ast.iter_child_nodes(node))

    _BODY_FIELDS = ("body", "orelse", "finalbody")

    def _walk_body(self, body: list[ast.stmt], scope: _Scope, code: str,
                   findings: list[Finding], cleared: set[int]) -> None:
        # Statements are processed in SOURCE ORDER, descending into
        # control-flow bodies, so a variable is always recorded before the
        # statement that uses it (e.g. `placeholders = …` then the `execute`
        # that interpolates it, both inside the same `for` loop).
        for stmt in body:
            self._walk_stmt(stmt, scope, code, findings, cleared)

    def _walk_stmt(self, stmt: ast.stmt, scope: _Scope, code: str,
                   findings: list[Finding], cleared: set[int]) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._enter_function(stmt, scope, code, findings, cleared)
            return
        if isinstance(stmt, ast.ClassDef):
            self._walk_body(stmt.body, scope, code, findings, cleared)
            return

        # For-loop targets drawn from a constant/sanitized iterable are
        # themselves sanitized; record before the loop body runs.
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            self._sanitize_for_target(stmt, scope)

        # Record the assignment this statement makes (its own level only).
        self._record_stmt_assignment(stmt, scope)

        # Grade execute-family calls that live in this statement's *own*
        # expressions (test/iter/value/return), not in nested bodies.
        for call in self._inline_calls(stmt):
            self._check_call(call, scope, code, findings, cleared)

        # Recurse into nested statement bodies in order.
        for field in self._BODY_FIELDS:
            for child in getattr(stmt, field, []) or []:
                self._walk_stmt(child, scope, code, findings, cleared)
        for handler in getattr(stmt, "handlers", []) or []:
            self._walk_body(handler.body, scope, code, findings, cleared)

    def _inline_calls(self, stmt: ast.stmt):
        """Call nodes in a statement's own expressions, not crossing into
        nested statement bodies or nested function/lambda scopes."""
        skip = set(self._BODY_FIELDS) | {"handlers"}
        roots: list[ast.AST] = []
        for field, value in ast.iter_fields(stmt):
            if field in skip:
                continue
            if isinstance(value, list):
                roots.extend(v for v in value if isinstance(v, ast.AST))
            elif isinstance(value, ast.AST):
                roots.append(value)
        for root in roots:
            stack = [root]
            while stack:
                node = stack.pop()
                if isinstance(node, ast.Call):
                    yield node
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.Lambda)):
                    stack.extend(ast.iter_child_nodes(node))

    def _enter_function(self, fn: ast.AST, scope: _Scope, code: str,
                        findings: list[Finding], cleared: set[int]) -> None:
        child = _Scope(parent=scope)
        self._prescan_const_collections(fn, child)
        self._prescan_guards(fn, child)
        self._walk_body(fn.body, child, code, findings, cleared)  # type: ignore[attr-defined]

    def _sanitize_for_target(self, node: ast.stmt, scope: _Scope) -> None:
        src = self._collection_source_name(node.iter)
        src_ok = (src is not None and (
            scope.is_sanitized(src) or scope.is_const_collection(src)
            or scope.lookup(src) == CONST)) or \
            self._classify(node.iter, scope) == CONST
        if src_ok:
            for tgt in ast.walk(node.target):
                if isinstance(tgt, ast.Name):
                    scope.sanitized.add(tgt.id)

    def _record_stmt_assignment(self, node: ast.stmt, scope: _Scope) -> None:
        if isinstance(node, ast.Assign):
            cls = self._classify(node.value, scope)
            lines = set(range(node.lineno,
                              (getattr(node, "end_lineno", None) or node.lineno) + 1))
            # A comprehension over a sanitized/constant source that itself
            # classifies constant yields a sanitized collection of identifiers
            # (fields = [c for c in ALLOWLIST if c in form]) — later
            # join()/iteration over it is safe.
            comp_collection = isinstance(
                node.value, (ast.ListComp, ast.SetComp, ast.DictComp)) and cls == CONST
            schema_allowlist = self._is_schema_allowlist(node.value)
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    scope.env[tgt.id] = cls
                    scope.assign_lines.setdefault(tgt.id, set()).update(lines)
                    if _is_literal_collection(node.value) or comp_collection \
                            or schema_allowlist:
                        scope.const_collections.add(tgt.id)
                    else:
                        scope.const_collections.discard(tgt.id)
        elif isinstance(node, ast.AnnAssign) and node.value is not None and \
                isinstance(node.target, ast.Name):
            scope.env[node.target.id] = self._classify(node.value, scope)
            if _is_literal_collection(node.value):
                scope.const_collections.add(node.target.id)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            prev = scope.lookup(node.target.id) or DYNAMIC
            add = self._classify(node.value, scope)
            scope.env[node.target.id] = CONST if (prev == CONST and add == CONST) else DYNAMIC
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._record_mutation(node.value, scope)

    def _record_mutation(self, node: ast.Call, scope: _Scope) -> None:
        if isinstance(node.func, ast.Attribute) and \
                node.func.attr in ("append", "extend", "insert", "add") and \
                isinstance(node.func.value, ast.Name):
            # Mutating a collection with non-constant items demotes it:
            # parts.append(f"name = '{name}'") must poison `parts`.
            target = node.func.value.id
            items = node.args[-1:] if node.func.attr != "insert" else node.args[1:]
            cls = CONST
            for item in items:
                if self._classify(item, scope) != CONST and \
                        not self._sanitized_value(item, scope):
                    cls = DYNAMIC
            prev = scope.lookup(target)
            if cls == DYNAMIC:
                scope.env[target] = DYNAMIC
                scope.const_collections.discard(target)
            elif prev is None:
                scope.env[target] = CONST

    # -- classification -----------------------------------------------------

    def _classify(self, e: ast.expr, scope: _Scope) -> str:
        if isinstance(e, ast.Constant):
            return CONST
        if isinstance(e, ast.JoinedStr):
            for part in e.values:
                if isinstance(part, ast.FormattedValue) and \
                        not self._sanitized_value(part.value, scope):
                    return DYNAMIC
            return CONST
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            left = self._classify(e.left, scope)
            right = self._classify(e.right, scope)
            return CONST if (left == CONST and right == CONST) else DYNAMIC
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
            left = self._classify(e.left, scope)
            right = self._classify(e.right, scope)
            if left == CONST and right == CONST:
                return CONST
            return DYNAMIC
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mult):
            # Replicating constant text/items stays constant regardless of
            # the count: ["?"] * len(ids), "?, " * n. The count side must be
            # count-like; the content side decides the classification.
            def countish(n: ast.expr) -> bool:
                if isinstance(n, ast.Constant) and isinstance(n.value, int):
                    return True
                return isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                    and n.func.id in ("len", "int")
            if countish(e.right):
                return self._classify(e.left, scope)
            if countish(e.left):
                return self._classify(e.right, scope)
            left = self._classify(e.left, scope)
            right = self._classify(e.right, scope)
            return CONST if (left == CONST and right == CONST) else DYNAMIC
        if isinstance(e, ast.Call):
            return self._classify_call(e, scope)
        if isinstance(e, ast.Name):
            if scope.is_sanitized(e.id):
                return CONST
            return scope.lookup(e.id) or DYNAMIC
        if isinstance(e, ast.IfExp):
            body = self._classify(e.body, scope)
            orelse = self._classify(e.orelse, scope)
            return CONST if (body == CONST and orelse == CONST) else DYNAMIC
        if isinstance(e, ast.Subscript):
            if isinstance(e.value, ast.Name) and scope.is_const_collection(e.value.id):
                return CONST
            return DYNAMIC
        if isinstance(e, (ast.Tuple, ast.List, ast.Set)):
            return CONST if all(self._classify(x, scope) == CONST for x in e.elts) else DYNAMIC
        if isinstance(e, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
            return self._classify_comprehension(e, scope)
        return DYNAMIC

    def _classify_call(self, e: ast.Call, scope: _Scope) -> str:
        if isinstance(e.func, ast.Attribute):
            recv = e.func.value
            if e.func.attr == "format":
                if self._classify(recv, scope) != CONST:
                    return DYNAMIC
                args_ok = all(self._sanitized_value(a, scope) for a in e.args) and \
                    all(kw.value is not None and self._sanitized_value(kw.value, scope)
                        for kw in e.keywords)
                return CONST if args_ok else DYNAMIC
            if e.func.attr == "join":
                if self._classify(recv, scope) != CONST:
                    return DYNAMIC
                if len(e.args) == 1:
                    arg = e.args[0]
                    if isinstance(arg, (ast.List, ast.Tuple, ast.Set)) and \
                            all(self._classify(x, scope) == CONST for x in arg.elts):
                        return CONST
                    if isinstance(arg, ast.Name) and (
                            scope.is_const_collection(arg.id)
                            or scope.lookup(arg.id) == CONST
                            or scope.is_sanitized(arg.id)):
                        return CONST
                    if isinstance(arg, (ast.GeneratorExp, ast.ListComp)):
                        return self._classify_comprehension_join(arg, scope)
                    # ", ".join(["?"] * len(ids)) and similar expressions
                    if self._classify(arg, scope) == CONST:
                        return CONST
                return DYNAMIC
            if e.func.attr == "get" and isinstance(recv, ast.Name) and \
                    scope.is_const_collection(recv.id):
                # dict-allowlist lookup: SORT_COLS.get(col, "name")
                return CONST
            if e.func.attr in ("strip", "rstrip", "lstrip", "upper", "lower"):
                return self._classify(recv, scope)
        if isinstance(e.func, ast.Name) and e.func.id in _SAFE_CASTS:
            return CONST
        if isinstance(e.func, ast.Name) and \
                e.func.id in ("list", "sorted", "set", "tuple", "frozenset") and e.args:
            # Reordering/copying a sanitized or constant collection of
            # identifiers keeps it sanitized: sorted(fields), list(form.keys())
            src = self._collection_source_name(e)
            if src and (scope.is_sanitized(src) or scope.is_const_collection(src)
                        or scope.lookup(src) == CONST):
                return CONST
        return DYNAMIC

    def _classify_comprehension(self, comp, scope: _Scope) -> str:
        """A comprehension is constant-derived iff every yielded element is
        constant or drawn from a sanitized/constant source collection.

        Covers ", ".join(f"{c} = ?" for c in fields),
        fields = [name for name in ALLOWLIST if name in form], and
        fields = {k: form[k] for k in ALLOWLIST if k in form} (iterating a
        dict yields its keys, so the key expression is what matters)."""
        child = _Scope(parent=scope)
        for gen in comp.generators:
            src = self._collection_source_name(gen.iter)
            src_ok = (src is not None and (
                scope.is_sanitized(src) or scope.is_const_collection(src)
                or scope.lookup(src) == CONST)) or \
                self._classify(gen.iter, scope) == CONST
            if src_ok:
                for tgt in ast.walk(gen.target):
                    if isinstance(tgt, ast.Name):
                        child.sanitized.add(tgt.id)
            # membership conditions inside the comprehension also sanitize:
            # (c for c in cols if c in ALLOWED)
            for cond in gen.ifs:
                self._prescan_guards(ast.Module(body=[ast.Expr(value=cond)],
                                                type_ignores=[]), child)
        # A dict comprehension iterated by join()/for yields its KEYS.
        elt = comp.key if isinstance(comp, ast.DictComp) else comp.elt
        return self._classify(elt, child)

    # kept for callers/tests referencing the old name
    _classify_comprehension_join = _classify_comprehension

    def _sanitized_value(self, e: ast.expr, scope: _Scope) -> bool:
        """Is this interpolated value safe to embed in SQL text?"""
        if isinstance(e, ast.Constant):
            return True
        # Anything the classifier proves constant-derived is safe to embed,
        # e.g. ", ".join("?" * len(ids)) — placeholder text, not user data.
        if self._classify(e, scope) == CONST:
            return True
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and \
                e.func.id in _SAFE_CASTS:
            return True
        if isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name) and \
                scope.is_const_collection(e.value.id):
            return True
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and \
                e.func.attr == "get" and isinstance(e.func.value, ast.Name) and \
                scope.is_const_collection(e.func.value.id):
            return True
        if isinstance(e, ast.Call):
            # list(form.keys()) / sorted(fields) over a sanitized source
            src = self._collection_source_name(e)
            if src and scope.is_sanitized(src):
                return True
        if isinstance(e, ast.Name):
            if scope.is_sanitized(e.id):
                return True
            # A name that provably holds constant-derived text (e.g. the
            # result of a dict-allowlist lookup) is safe to interpolate.
            if scope.lookup(e.id) == CONST:
                return True
        if isinstance(e, ast.IfExp):
            # e.g. col if col in ALLOWED else "id"
            test = e.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and \
                    isinstance(test.ops[0], (ast.In, ast.NotIn)):
                return True
        return False

    # -- exec-call check ----------------------------------------------------

    _RULE_BY_SHAPE = [
        (ast.JoinedStr, "sql-ast.fstring-query", "f-string interpolated into SQL query"),
        (ast.BinOp, None, None),  # refined below
        (ast.Call, "sql-ast.format-query", "str.format()/dynamic call builds SQL query"),
        (ast.Name, "sql-ast.dynamic-variable-query",
         "query variable is not provably constant"),
    ]

    def _check_call(self, call: ast.Call, scope: _Scope, code: str,
                    findings: list[Finding], cleared: set[int]) -> None:
        if not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr not in EXEC_METHODS or not call.args:
            return
        query = call.args[0]
        if self._classify(query, scope) == CONST:
            end = getattr(call, "end_lineno", None) or call.lineno
            cleared.update(range(call.lineno, end + 1))
            # Semgrep's assigned-variable rules report the assignment line,
            # so a cleared Name argument also clears where it was built.
            if isinstance(query, ast.Name):
                cleared.update(scope.lines_for(query.id))
            return
        rule_id, msg = "sql-ast.dynamic-query", "non-constant SQL query expression"
        if isinstance(query, ast.JoinedStr):
            rule_id, msg = "sql-ast.fstring-query", "f-string interpolated into SQL query"
        elif isinstance(query, ast.BinOp) and isinstance(query.op, ast.Add):
            rule_id, msg = "sql-ast.concat-query", "string concatenation builds SQL query"
        elif isinstance(query, ast.BinOp) and isinstance(query.op, ast.Mod):
            rule_id, msg = "sql-ast.percent-format-query", "%-formatting builds SQL query"
        elif isinstance(query, ast.Call):
            rule_id, msg = "sql-ast.format-query", "dynamic call result used as SQL query"
        elif isinstance(query, ast.Name):
            rule_id, msg = ("sql-ast.dynamic-variable-query",
                            "query variable is not provably constant")
        snippet = ast.get_source_segment(code, call)
        findings.append(Finding(
            detector=self.name, rule_id=rule_id, message=msg,
            line=getattr(call, "lineno", None),
            snippet=(snippet or "")[:200] or None))

    # -- raw SQL ------------------------------------------------------------

    _PLACEHOLDER_RE = re.compile(r"\?|%s|%\(\w+\)s|:\w+|\$\d+")
    _TEMPLATE_RE = re.compile(r"\{[A-Za-z_]\w*\}|\$\{|\{\{")

    def _scan_raw_sql(self, code: str, task: TaskSpec) -> list[Finding]:
        text = code.strip().rstrip(";")
        findings: list[Finding] = []
        if self._TEMPLATE_RE.search(text):
            findings.append(Finding(
                detector=self.name, rule_id="sql-ast.template-in-sql",
                message="template/interpolation marker inside raw SQL",
                snippet=text[:200]))
            return findings
        if self._PLACEHOLDER_RE.search(text):
            return findings
        # No placeholders at all: user-supplied comparisons are inlined.
        try:
            import sqlglot
            from sqlglot import expressions as exp
            parsed = sqlglot.parse_one(text, read="sqlite")
            for cond in parsed.find_all(exp.Condition):
                if isinstance(cond, (exp.EQ, exp.Like, exp.GT, exp.LT, exp.GTE,
                                     exp.LTE, exp.In)) and \
                        any(isinstance(x, exp.Literal) for x in cond.args.values()
                            if isinstance(x, exp.Expression)):
                    findings.append(Finding(
                        detector=self.name, rule_id="sql-ast.inlined-literal",
                        message="literal inlined where a bound parameter is expected",
                        snippet=cond.sql()[:200]))
                    break
        except Exception:
            pass  # unparseable raw SQL is handled upstream as invalid
        return findings
