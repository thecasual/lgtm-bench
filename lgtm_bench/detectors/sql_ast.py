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


def _is_const_collection_value(node: ast.AST) -> bool:
    """True for a value that builds a constant identifier allowlist: a literal
    collection, or a constructor call wrapping one — ``set(("a","b"))``,
    ``frozenset({...})``, ``tuple([...])``, ``list((...))``. Constructors nest,
    so ``frozenset(set(("a",)))`` also qualifies."""
    if _is_literal_collection(node):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
            node.func.id in ("set", "frozenset", "tuple", "list") and \
            len(node.args) == 1 and not node.keywords:
        return _is_const_collection_value(node.args[0])
    return False


class _Scope:
    """Best-effort, source-order model of one function/module scope."""

    def __init__(self, parent: "_Scope | None" = None):
        self.parent = parent
        self.env: dict[str, str] = {}            # name -> CONST | DYNAMIC
        self.const_collections: set[str] = set() # names bound to literal collections
        self.sanitized: set[str] = set()         # membership-guarded names
        self.assign_lines: dict[str, set[int]] = {}  # name -> assignment lines
        # Names bound *locally* by this scope's own binding forms (function
        # params, for-loop targets, comprehension targets). Such a binding
        # SHADOWS any same-named binding in an enclosing scope: a parent's
        # sanitization / constness must not leak onto a distinct local
        # variable that merely reuses the identifier.
        self.local_binds: set[str] = set()

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
            if name in s.local_binds:
                return None  # locally bound here; do not consult the parent
            s = s.parent
        return None

    def is_const_collection(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.const_collections:
                return True
            if name in s.local_binds:
                return False  # locally bound here; do not consult the parent
            s = s.parent
        return False

    def is_sanitized(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.sanitized:
                return True
            if name in s.local_binds:
                return False  # locally bound here; do not consult the parent
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
        # Names passed as the query argument to an execute-family call anywhere
        # in the tree. The return/assignment sink skips such names so a query
        # that is *both* built-and-executed is not double-reported.
        self._exec_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in EXEC_METHODS and node.args \
                    and isinstance(node.args[0], ast.Name):
                self._exec_names.add(node.args[0].id)
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
            if _is_const_collection_value(value) or \
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
        """Collect identifier-allowlist guards that actually gate flow.

        A single-name membership test (``x in ALLOW`` / ``x not in ALLOW``)
        sanitizes ``x`` for code AFTER the ``if`` ONLY when it is a *reject*
        branch — negative membership whose body unconditionally exits
        (``if x not in ALLOW: raise``). The *accept* branch case
        (``if x in ALLOW:`` — sink inside the body) is handled during the walk
        so the sanitization is scoped to the body, not the whole function.
        Positive-membership-with-exit is a BLOCKLIST (``if x in BLOCKED:
        raise``) and does NOT sanitize; an unenforced membership expression
        (``is_valid = x in {...}``) does not gate flow and does NOT sanitize.

        Subset guards over a whole collection (``set(fields) - ALLOWED``,
        ``set(fields) <= ALLOWED``, ``set(fields).issubset(ALLOWED)``) are
        order-independent allowlist checks and stay recognized wherever they
        appear (assignment or ``if`` test)."""
        for node in self._scope_walk(scope_node):
            if isinstance(node, ast.If):
                self._process_if_guard(node, scope)
            # subset guards over a whole collection of identifiers:
            #   set(fields) - ALLOWED / set(fields) <= ALLOWED /
            #   set(fields).issubset(ALLOWED)
            # Only a PROVEN constant collection is an allowlist. A name is not
            # trusted merely for being ALLCAPS — a model can bind user data to
            # an uppercase name, and spelling is not a safety guarantee.
            allowish = lambda n: _is_const_collection_value(n) or (
                isinstance(n, ast.Name) and scope.is_const_collection(n.id))
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

    def _process_if_guard(self, node: ast.If, scope: _Scope) -> None:
        """Reject-branch allowlist: ``if x not in ALLOW: <exit>`` validates x
        for all code after the ``if``. Positive membership with an exiting body
        is a blocklist and is intentionally NOT sanitized here."""
        if not self._body_exits(node.body):
            return
        for guarded, positive in self._membership_guards_in_test(node.test, scope):
            if not positive:
                scope.sanitized.add(guarded)

    def _accept_branch_names(self, node: ast.If, scope: _Scope) -> set[str]:
        """Accept-branch allowlist: ``if x in ALLOW:`` validates x for the code
        INSIDE the body only. A body that rejects *immediately* (its first
        statement is a bare raise/return/continue/break guard clause) is a
        blocklist instead (``if x in BLOCKED: raise``) and validates nothing;
        an accept branch does real work — including the sink — before any
        return."""
        if self._body_rejects_immediately(node.body):
            return set()
        out: set[str] = set()
        for guarded, positive in self._membership_guards_in_test(node.test, scope):
            if positive:
                out.add(guarded)
        return out

    @staticmethod
    def _body_exits(body: list[ast.stmt]) -> bool:
        """True if the block unconditionally leaves the surrounding flow via a
        top-level raise/return/continue/break (statements after it are dead, so
        the reject path is taken for every value that reaches the test). Used
        for the negative-membership reject branch (``if x not in ALLOW: ...
        raise``), where validation holds for all code after the ``if``."""
        return any(isinstance(s, (ast.Raise, ast.Return, ast.Continue, ast.Break))
                   for s in body)

    @staticmethod
    def _body_rejects_immediately(body: list[ast.stmt]) -> bool:
        """True if the block is a pure guard clause: its FIRST statement is an
        unconditional exit. Distinguishes a positive-membership blocklist
        (``if x in BLOCKED: raise``) from an accept branch that uses x first."""
        return bool(body) and isinstance(
            body[0], (ast.Raise, ast.Return, ast.Continue, ast.Break))

    def _membership_guards_in_test(self, test: ast.expr, scope: _Scope):
        """Yield ``(name, is_positive)`` for each single-name membership guard
        in an ``if`` test against a recognized allowlist. ``is_positive`` is
        True for ``x in ALLOW`` and False for ``x not in ALLOW``."""
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and \
                isinstance(test.ops[0], (ast.In, ast.NotIn)):
            guarded = self._guarded_name(test.left)
            comp = test.comparators[0]
            if guarded is not None and self._is_allowlist_comparator(comp, scope):
                yield guarded, isinstance(test.ops[0], ast.In)

    def _is_allowlist_comparator(self, comp: ast.expr, scope: _Scope) -> bool:
        """Is the right-hand side of a membership test a constant allowlist? A
        literal/constructor collection, a const/schema/dict const-collection
        name, or a ``NAME.keys()``/``.values()`` view over such a collection
        (BUG #5). A name is trusted only when PROVEN constant — not for being
        ALLCAPS, since spelling is not a safety guarantee."""
        if _is_const_collection_value(comp):
            return True
        src = self._collection_source_name(comp)
        if src is not None and scope.is_const_collection(src):
            return True
        return False

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

        # Grade a tainted SQL string that is RETURNED or assigned as the final
        # query without ever reaching execute() (query-builder helpers).
        self._check_query_sink(stmt, scope, code, findings)

        # Recurse into nested statement bodies in order. For an `if x in ALLOW:`
        # accept-branch guard the guarded name is sanitized only WITHIN the body
        # (not the orelse, not code after the if): add it for the body recursion
        # and remove it afterward.
        accept_names: set[str] = set()
        if isinstance(stmt, ast.If):
            accept_names = self._accept_branch_names(stmt, scope) - scope.sanitized
        for field in self._BODY_FIELDS:
            added = accept_names if field == "body" else set()
            scope.sanitized |= added
            for child in getattr(stmt, field, []) or []:
                self._walk_stmt(child, scope, code, findings, cleared)
            scope.sanitized -= added
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
        # Parameters are locally bound and thus shadow any enclosing-scope
        # binding of the same name (a module-level `k` marked sanitized must
        # not bless a function parameter also named `k`).
        args = getattr(fn, "args", None)
        if args is not None:
            for group in (getattr(args, "posonlyargs", None), args.args,
                          getattr(args, "kwonlyargs", None)):
                for a in group or []:
                    child.local_binds.add(a.arg)
            for a in (args.vararg, args.kwarg):
                if a is not None:
                    child.local_binds.add(a.arg)
            # A parameter whose DEFAULT is a constant collection is an allowlist
            # inside the body (BUG #6): `def f(..., allowed=("a","b")): ...`.
            # A parameter with no default (or a non-constant default) stays
            # tainted — it is NOT recorded as a const-collection.
            for name, default in self._param_defaults(args):
                if _is_const_collection_value(default):
                    child.const_collections.add(name)
        self._prescan_const_collections(fn, child)
        self._prescan_guards(fn, child)
        self._walk_body(fn.body, child, code, findings, cleared)  # type: ignore[attr-defined]

    @staticmethod
    def _param_defaults(args: ast.arguments):
        """Yield ``(param_name, default_node)`` for parameters that carry a
        default. Positional defaults align to the tail of posonly+args;
        keyword-only defaults align to kwonlyargs (None where absent)."""
        positional = list(getattr(args, "posonlyargs", None) or []) + list(args.args or [])
        defaults = list(args.defaults or [])
        if defaults:
            for a, d in zip(positional[-len(defaults):], defaults):
                yield a.arg, d
        for a, d in zip(getattr(args, "kwonlyargs", None) or [],
                        getattr(args, "kw_defaults", None) or []):
            if d is not None:
                yield a.arg, d

    def _sanitize_for_target(self, node: ast.stmt, scope: _Scope) -> None:
        src = self._collection_source_name(node.iter)
        src_ok = (src is not None and (
            scope.is_sanitized(src) or scope.is_const_collection(src)
            or scope.lookup(src) == CONST)) or \
            self._classify(node.iter, scope) == CONST
        for tgt in ast.walk(node.target):
            if isinstance(tgt, ast.Name):
                # A for-target is a local binding: it shadows any enclosing
                # sanitization of the same name (recorded even when the source
                # is not an allowlist, so an unvalidated loop var stays tainted).
                scope.local_binds.add(tgt.id)
                if src_ok:
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
            # A value that is itself safe to interpolate makes the variable safe
            # to interpolate — e.g. an allowlist-guarded conditional expression
            # bound to a temp before use (`safe = col if col in ALLOW else "x"`;
            # BUG #11 safe twin). Only the RESULT temp is blessed, never the raw
            # operand.
            value_ok = cls != CONST and self._sanitized_value(node.value, scope)
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    scope.env[tgt.id] = cls
                    scope.assign_lines.setdefault(tgt.id, set()).update(lines)
                    if _is_const_collection_value(node.value) or comp_collection \
                            or schema_allowlist:
                        scope.const_collections.add(tgt.id)
                    else:
                        scope.const_collections.discard(tgt.id)
                    if value_ok:
                        scope.sanitized.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and node.value is not None and \
                isinstance(node.target, ast.Name):
            scope.env[node.target.id] = self._classify(node.value, scope)
            if _is_const_collection_value(node.value):
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
                        not self._numeric_format_spec(part) and \
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
                # dict-allowlist lookup: SORT_COLS.get(col, "name"). Safe only
                # when the fallback is itself constant/sanitized — a
                # user-controlled default (SORT_COLS.get(col, user_val)) flows
                # straight into SQL for any key absent from the allowlist.
                if len(e.args) >= 2 and \
                        self._classify(e.args[1], scope) != CONST and \
                        not self._sanitized_value(e.args[1], scope):
                    return DYNAMIC
                return CONST
            if e.func.attr in ("strip", "rstrip", "lstrip", "upper", "lower"):
                return self._classify(recv, scope)
        if isinstance(e.func, ast.Name) and e.func.id in _SAFE_CASTS:
            return CONST
        if isinstance(e.func, ast.Name) and e.func.id == "str" and e.args:
            # str(int(x)) / str(len(x)) — a numeric cast can't carry SQL, and
            # str() of an already-constant value stays constant.
            return self._classify(e.args[0], scope)
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
            for tgt in ast.walk(gen.target):
                if isinstance(tgt, ast.Name):
                    # Comprehension targets are local bindings: they shadow any
                    # enclosing-scope sanitization of the same identifier.
                    child.local_binds.add(tgt.id)
                    if src_ok:
                        child.sanitized.add(tgt.id)
            # POSITIVE membership conditions inside the comprehension sanitize:
            # (c for c in cols if c in ALLOWED). A `not in FORBIDDEN` filter is a
            # blocklist and must NOT sanitize c (BUG #4). The allowlist name is
            # resolved in the enclosing scope; the target is blessed in `child`.
            for cond in gen.ifs:
                for guarded, positive in self._membership_guards_in_test(cond, scope):
                    if positive:
                        child.sanitized.add(guarded)
        # A dict comprehension iterated by join()/for yields its KEYS.
        elt = comp.key if isinstance(comp, ast.DictComp) else comp.elt
        return self._classify(elt, child)

    # kept for callers/tests referencing the old name
    _classify_comprehension_join = _classify_comprehension

    # Format-spec type chars that coerce the value to a number at format time,
    # so the interpolated value cannot carry SQL text (e.g. f"LIMIT {n:d}").
    _NUMERIC_FMT = set("dnboxXeEfFgG%")

    def _numeric_format_spec(self, part: ast.FormattedValue) -> bool:
        """True if an f-string field has a constant numeric format spec like
        ``{n:d}`` — format(n, 'd') raises unless n is an int, so it can't
        inject. Also covers a bare ``{f:.2f}`` etc. Conversion (!r/!s/!a) is
        NOT numeric."""
        if part.conversion not in (-1, ord("r"), ord("s"), ord("a")):
            return False
        spec = part.format_spec
        if not isinstance(spec, ast.JoinedStr) or len(spec.values) != 1:
            return False
        node = spec.values[0]
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return False
        text = node.value.strip()
        return bool(text) and text[-1] in self._NUMERIC_FMT \
            and part.conversion == -1

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
            # ALLOW.get(key) / ALLOW.get(key, <const>) is safe; a
            # user-controlled fallback flows through unchecked.
            if len(e.args) >= 2 and \
                    self._classify(e.args[1], scope) != CONST and \
                    not self._sanitized_value(e.args[1], scope):
                return False
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
            # e.g. col if col in ALLOWED else "id". A membership test blesses
            # the expression ONLY when both branch VALUES are safe: a constant,
            # the very name the test guards, or independently sanitized. A
            # branch returning a *different* unvalidated name (e.g.
            # `sort_col if direction in (...) else sort_col`) is still tainted.
            test = e.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and \
                    isinstance(test.ops[0], (ast.In, ast.NotIn)):
                guarded = self._guarded_name(test.left)

                def _branch_ok(b: ast.expr) -> bool:
                    if isinstance(b, ast.Constant):
                        return True
                    if guarded is not None and isinstance(b, ast.Name) and \
                            b.id == guarded:
                        return True
                    return self._sanitized_value(b, scope)

                if _branch_ok(e.body) and _branch_ok(e.orelse):
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

    # -- return / assignment sink -------------------------------------------

    # SQL statement keywords that mark a string as query text rather than an
    # ordinary value. ``ORDER\s+BY`` matches "ORDER BY" across arbitrary space.
    _SQL_KW_RE = re.compile(
        r"\b(SELECT|INSERT|UPDATE|DELETE|WHERE|ORDER\s+BY|SET|FROM)\b", re.I)

    @staticmethod
    def _node_sql_text(node: ast.expr) -> str:
        """All string-constant fragments within an expression, concatenated —
        the literal SQL skeleton of an f-string / concat / join build."""
        parts: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                parts.append(sub.value)
        return " ".join(parts)

    def _check_query_sink(self, stmt: ast.stmt, scope: _Scope, code: str,
                          findings: list[Finding]) -> None:
        """Conservatively flag a ``return <expr>`` / ``name = <expr>`` that
        builds SQL text with tainted interpolation but is never executed here.

        Only fires when a query-bearing sub-expression classifies DYNAMIC and
        its literal skeleton contains a SQL keyword; a constant/parameterized/
        allowlisted build classifies CONST and is left alone."""
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            value: ast.expr = stmt.value
            target_name: str | None = None
        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and \
                isinstance(stmt.targets[0], ast.Name):
            value = stmt.value
            target_name = stmt.targets[0].id
        else:
            return
        # If the value is (or wraps) an execute-family call, _check_call has
        # already graded it — do not double-report.
        for sub in ast.walk(value):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                    and sub.func.attr in EXEC_METHODS:
                return
        # A variable that is separately executed elsewhere is reported at the
        # execute() call; skip its build assignment to avoid double-counting.
        if target_name is not None and target_name in self._exec_names:
            return
        # Consider the query string components: for a returned/assigned tuple
        # (query, params) only the query element matters, not the params.
        candidates = list(value.elts) if isinstance(value, (ast.Tuple, ast.List)) \
            else [value]
        for cand in candidates:
            if self._classify(cand, scope) != DYNAMIC:
                continue
            text = self._node_sql_text(cand)
            if not text or not self._SQL_KW_RE.search(text):
                continue
            snippet = ast.get_source_segment(code, stmt)
            findings.append(Finding(
                detector=self.name, rule_id="sql-ast.tainted-query-builder",
                message="tainted value interpolated into a returned/assigned "
                        "SQL query string",
                line=getattr(stmt, "lineno", None),
                snippet=(snippet or "")[:200] or None))
            return  # one finding per statement

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
