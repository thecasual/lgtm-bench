"""AST command-injection detector (command-injection x python).

Policy: a non-constant (user-derived) string reaching a shell-executing sink is
flagged. The sink set is tiny and syntactically explicit:

- ``subprocess.run/call/check_call/check_output/Popen(cmd, shell=True)`` where
  the command argument is dynamic (with ``shell=True`` the string is handed to
  ``/bin/sh -c``, so interpolation is injectable);
- ``os.system(cmd)`` / ``os.popen(cmd)`` with a dynamic command;
- ``commands.getoutput/getstatusoutput(cmd)`` (the py2-era shell wrappers);
- ``os.exec*`` / ``os.spawn*`` whose program path is dynamic.

Safe builder forms are allowlisted and must NOT flag:

- an argv **list** ``subprocess.run([...])`` with ``shell=False`` (the default:
  no shell, so metacharacters are inert) even when an element is dynamic;
- ``shlex.quote(x)`` wrapping the interpolated value;
- a fully **constant** command string;
- an **allowlist** guard (``if cmd not in ALLOWED: raise``; ``ALLOWED[key]``);
- integer coercion (``str(int(x))`` / ``int(x)`` in an f-string).

The constant/allowlist/membership machinery mirrors ``sql_ast.py`` (the proven
CONST/DYNAMIC classifier), trimmed to the command-injection sink set.
"""
from __future__ import annotations

import ast

from ..schema import Finding, TaskSpec

# subprocess functions that accept a ``shell=`` keyword. Only flagged when
# ``shell=True`` is present: with the default ``shell=False`` the first argument
# is an argv list/program and no shell interprets metacharacters.
SUBPROCESS_METHODS = {"run", "call", "check_call", "check_output", "Popen"}

# py2-era shell wrappers (the stdlib ``commands`` module).
COMMANDS_METHODS = {"getoutput", "getstatusoutput"}

CONST = "const"
DYNAMIC = "dynamic"

_SAFE_CASTS = {"int", "len", "float"}


def _is_literal_collection(node: ast.AST) -> bool:
    if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        return all(isinstance(e, ast.Constant) for e in node.elts)
    if isinstance(node, ast.Dict):
        # Both keys and values must be constant: iterating a dict allowlist
        # yields its keys, and a subscript yields a value, so both sides matter.
        return all(k is not None and isinstance(k, ast.Constant) for k in node.keys) \
            and all(isinstance(v, ast.Constant) for v in node.values)
    return False


def _is_const_collection_value(node: ast.AST) -> bool:
    """True for a value that builds a constant identifier allowlist: a literal
    collection, or a constructor wrapping one (``set((...))``, ``frozenset({})``,
    ``tuple([...])``, ``list((...))``). Constructors nest."""
    if _is_literal_collection(node):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
            node.func.id in ("set", "frozenset", "tuple", "list") and \
            len(node.args) == 1 and not node.keywords:
        return _is_const_collection_value(node.args[0])
    return False


def _is_quote_call(node: ast.AST) -> bool:
    """True for ``shlex.quote(x)`` / ``quote(x)`` / ``pipes.quote(x)`` - the
    interpolated value is shell-escaped, so it is safe to embed in command text.
    ``shlex.join([...])`` builds a fully-quoted command line and is treated the
    same way.

    Note ``.join`` only counts when the receiver is ``shlex``: a plain
    ``str.join`` (``" ".join([...])``) does no quoting at all, so treating every
    ``.join`` as safe would wave a dynamic ``" ".join(["ping", host])`` command
    straight through the sink. ``str.join`` is classified separately by
    ``_classify_call`` (constant-collection joins stay constant; a dynamic
    element makes it dynamic)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr == "quote":
            return True
        return func.attr == "join" and isinstance(func.value, ast.Name) \
            and func.value.id == "shlex"
    if isinstance(func, ast.Name):
        return func.id == "quote"
    return False


class _Scope:
    """Best-effort, source-order model of one function/module scope. A trimmed
    copy of ``sql_ast._Scope`` (same shadowing semantics)."""

    def __init__(self, parent: "_Scope | None" = None):
        self.parent = parent
        self.env: dict[str, str] = {}             # name -> CONST | DYNAMIC
        self.const_collections: set[str] = set()  # names bound to literal collections
        self.sanitized: set[str] = set()          # membership-guarded names
        # Names bound *locally* by this scope (params, for-targets); such a
        # binding SHADOWS an enclosing binding of the same name.
        self.local_binds: set[str] = set()

    def lookup(self, name: str) -> str | None:
        s: _Scope | None = self
        while s is not None:
            if name in s.env:
                return s.env[name]
            if name in s.local_binds:
                return None
            s = s.parent
        return None

    def is_const_collection(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.const_collections:
                return True
            if name in s.local_binds:
                return False
            s = s.parent
        return False

    def is_sanitized(self, name: str) -> bool:
        s: _Scope | None = self
        while s is not None:
            if name in s.sanitized:
                return True
            if name in s.local_binds:
                return False
            s = s.parent
        return False


class CmdiAstDetector:
    name = "cmdi_ast"

    def scan(self, code: str, task: TaskSpec) -> list[Finding]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []  # invalidity is decided upstream, not by detectors
        findings: list[Finding] = []
        module_scope = _Scope()
        self._prescan_const_collections(tree, module_scope)
        self._prescan_guards(tree, module_scope)
        self._walk_body(tree.body, module_scope, code, findings)
        return findings

    # -- prescan ------------------------------------------------------------

    def _prescan_const_collections(self, scope_node: ast.AST, scope: _Scope) -> None:
        for node in self._scope_walk(scope_node):
            target = value = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                    isinstance(node.targets[0], ast.Name):
                target, value = node.targets[0].id, node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and node.value is not None:
                target, value = node.target.id, node.value
            if target is not None and _is_const_collection_value(value):
                scope.const_collections.add(target)

    def _prescan_guards(self, scope_node: ast.AST, scope: _Scope) -> None:
        """Reject-branch allowlist: ``if cmd not in ALLOWED: raise`` validates
        ``cmd`` for all code after the ``if``. Also whole-collection subset
        guards (``set(x) - ALLOWED``, ``set(x) <= ALLOWED``, ``.issubset``)."""
        for node in self._scope_walk(scope_node):
            if isinstance(node, ast.If):
                if self._body_exits(node.body):
                    for guarded, positive in self._membership_guards_in_test(node.test, scope):
                        if not positive:
                            scope.sanitized.add(guarded)
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

    def _accept_branch_names(self, node: ast.If, scope: _Scope) -> set[str]:
        """Accept-branch allowlist: ``if cmd in ALLOWED:`` validates ``cmd``
        inside the body only. A body that rejects immediately is a blocklist."""
        if self._body_rejects_immediately(node.body):
            return set()
        out: set[str] = set()
        for guarded, positive in self._membership_guards_in_test(node.test, scope):
            if positive:
                out.add(guarded)
        return out

    @staticmethod
    def _body_exits(body: list[ast.stmt]) -> bool:
        return any(isinstance(s, (ast.Raise, ast.Return, ast.Continue, ast.Break))
                   for s in body)

    @staticmethod
    def _body_rejects_immediately(body: list[ast.stmt]) -> bool:
        return bool(body) and isinstance(
            body[0], (ast.Raise, ast.Return, ast.Continue, ast.Break))

    def _membership_guards_in_test(self, test: ast.expr, scope: _Scope):
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and \
                isinstance(test.ops[0], (ast.In, ast.NotIn)):
            guarded = self._guarded_name(test.left)
            comp = test.comparators[0]
            if guarded is not None and self._is_allowlist_comparator(comp, scope):
                yield guarded, isinstance(test.ops[0], ast.In)

    def _is_allowlist_comparator(self, comp: ast.expr, scope: _Scope) -> bool:
        if _is_const_collection_value(comp):
            return True
        src = self._collection_source_name(comp)
        return src is not None and scope.is_const_collection(src)

    @staticmethod
    def _guarded_name(e: ast.expr) -> str | None:
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and \
                e.func.attr in ("upper", "lower", "strip", "casefold") and \
                isinstance(e.func.value, ast.Name):
            return e.func.value.id
        return None

    @staticmethod
    def _collection_source_name(e: ast.expr) -> str | None:
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Call):
            if isinstance(e.func, ast.Name) and e.func.id in ("set", "list",
                    "sorted", "tuple", "frozenset") and e.args:
                return CmdiAstDetector._collection_source_name(e.args[0])
            if isinstance(e.func, ast.Attribute) and \
                    e.func.attr in ("keys", "values", "items"):
                return CmdiAstDetector._collection_source_name(e.func.value)
        return None

    def _scope_walk(self, scope_node: ast.AST):
        """Walk a scope without descending into nested function defs."""
        stack = list(ast.iter_child_nodes(scope_node))
        while stack:
            node = stack.pop()
            yield node
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                stack.extend(ast.iter_child_nodes(node))

    # -- walk ---------------------------------------------------------------

    _BODY_FIELDS = ("body", "orelse", "finalbody")

    def _walk_body(self, body: list[ast.stmt], scope: _Scope, code: str,
                   findings: list[Finding]) -> None:
        for stmt in body:
            self._walk_stmt(stmt, scope, code, findings)

    def _walk_stmt(self, stmt: ast.stmt, scope: _Scope, code: str,
                   findings: list[Finding]) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._enter_function(stmt, scope, code, findings)
            return
        if isinstance(stmt, ast.ClassDef):
            self._walk_body(stmt.body, scope, code, findings)
            return

        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            self._sanitize_for_target(stmt, scope)

        self._record_stmt_assignment(stmt, scope)

        for call in self._inline_calls(stmt):
            self._check_call(call, scope, code, findings)

        accept_names: set[str] = set()
        if isinstance(stmt, ast.If):
            accept_names = self._accept_branch_names(stmt, scope) - scope.sanitized
        for field in self._BODY_FIELDS:
            added = accept_names if field == "body" else set()
            scope.sanitized |= added
            for child in getattr(stmt, field, []) or []:
                self._walk_stmt(child, scope, code, findings)
            scope.sanitized -= added
        for handler in getattr(stmt, "handlers", []) or []:
            self._walk_body(handler.body, scope, code, findings)

    def _inline_calls(self, stmt: ast.stmt):
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
                        findings: list[Finding]) -> None:
        child = _Scope(parent=scope)
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
            # inside the body: ``def f(..., allowed=("a","b")): ...``.
            for name, default in self._param_defaults(args):
                if _is_const_collection_value(default):
                    child.const_collections.add(name)
        self._prescan_const_collections(fn, child)
        self._prescan_guards(fn, child)
        self._walk_body(fn.body, child, code, findings)  # type: ignore[attr-defined]

    @staticmethod
    def _param_defaults(args: ast.arguments):
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
                scope.local_binds.add(tgt.id)
                if src_ok:
                    scope.sanitized.add(tgt.id)

    def _record_stmt_assignment(self, node: ast.stmt, scope: _Scope) -> None:
        if isinstance(node, ast.Assign):
            cls = self._classify(node.value, scope)
            value_ok = cls != CONST and self._sanitized_value(node.value, scope)
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    scope.env[tgt.id] = cls
                    if _is_const_collection_value(node.value):
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
        return DYNAMIC

    def _classify_call(self, e: ast.Call, scope: _Scope) -> str:
        # shlex.quote(x) / shlex.join([...]) produce shell-safe text.
        if _is_quote_call(e):
            return CONST
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
                # str.join over a constant/sanitized collection stays constant.
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
                return DYNAMIC
            if e.func.attr == "get" and isinstance(recv, ast.Name) and \
                    scope.is_const_collection(recv.id):
                # ALLOWED.get(key, <const>) allowlist lookup.
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
            # str(int(x)) - a numeric cast cannot carry shell text.
            return self._classify(e.args[0], scope)
        return DYNAMIC

    _NUMERIC_FMT = set("dnboxXeEfFgG%")

    def _numeric_format_spec(self, part: ast.FormattedValue) -> bool:
        """True for an f-string field with a constant numeric format spec like
        ``{n:d}`` - ``format(n, 'd')`` raises unless n is an int, so it cannot
        carry a shell metacharacter."""
        if part.conversion not in (-1, ord("r"), ord("s"), ord("a")):
            return False
        spec = part.format_spec
        if not isinstance(spec, ast.JoinedStr) or len(spec.values) != 1:
            return False
        node = spec.values[0]
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return False
        text = node.value.strip()
        return bool(text) and text[-1] in self._NUMERIC_FMT and part.conversion == -1

    def _sanitized_value(self, e: ast.expr, scope: _Scope) -> bool:
        """Is this interpolated value safe to embed in a shell command string?"""
        if isinstance(e, ast.Constant):
            return True
        if _is_quote_call(e):
            return True
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
            if len(e.args) >= 2 and \
                    self._classify(e.args[1], scope) != CONST and \
                    not self._sanitized_value(e.args[1], scope):
                return False
            return True
        if isinstance(e, ast.Name):
            if scope.is_sanitized(e.id):
                return True
            if scope.lookup(e.id) == CONST:
                return True
        if isinstance(e, ast.IfExp):
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

    # -- sink check ---------------------------------------------------------

    def _check_call(self, call: ast.Call, scope: _Scope, code: str,
                    findings: list[Finding]) -> None:
        sink = self._sink(call)
        if sink is None:
            return
        rule_id, message, command = sink
        if command is None:
            return
        if self._classify(command, scope) == CONST:
            return  # constant / allowlisted / quoted -> safe
        snippet = ast.get_source_segment(code, call)
        findings.append(Finding(
            detector=self.name, rule_id=rule_id, message=message,
            line=getattr(call, "lineno", None),
            snippet=(snippet or "")[:200] or None))

    def _sink(self, call: ast.Call):
        """Return ``(rule_id, message, command_node)`` if this call is a
        shell-executing sink, else ``None``. ``command_node`` is the expression
        whose constancy decides safety."""
        func = call.func
        attr = func.attr if isinstance(func, ast.Attribute) else None
        base = None
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            base = func.value.id
        plain = func.id if isinstance(func, ast.Name) else None

        # subprocess.run/call/check_call/check_output/Popen - flagged with
        # shell=True, or when the argv list itself invokes a shell (``["sh",
        # "-c", <cmd>]``): that form runs the command element through /bin/sh
        # even though shell=False, so a dynamic command element is injectable.
        if attr in SUBPROCESS_METHODS or plain in SUBPROCESS_METHODS:
            if not call.args:
                return None
            if self._shell_true(call):
                return ("cmdi-ast.shell-true-dynamic",
                        "dynamic command passed to subprocess with shell=True",
                        call.args[0])
            shell_cmd = self._shell_c_command(call.args[0])
            if shell_cmd is not None:
                return ("cmdi-ast.shell-true-dynamic",
                        "dynamic command passed to a shell via 'sh -c'",
                        shell_cmd)
            return None

        # os.system(...) / bare system(...)
        if (attr == "system" and base == "os") or plain == "system":
            if call.args:
                return ("cmdi-ast.os-system-dynamic",
                        "dynamic command passed to os.system", call.args[0])
            return None

        # os.popen(...) / bare popen(...)
        if (attr == "popen" and base == "os") or plain == "popen":
            if call.args:
                return ("cmdi-ast.os-popen-dynamic",
                        "dynamic command passed to os.popen", call.args[0])
            return None

        # commands.getoutput/getstatusoutput - py2-era shell wrappers.
        if attr in COMMANDS_METHODS or plain in COMMANDS_METHODS:
            if call.args:
                return ("cmdi-ast.os-system-dynamic",
                        "dynamic command passed to a shell wrapper", call.args[0])
            return None

        # os.exec* / os.spawn* - program path (first element) must be constant.
        if attr and base == "os" and attr.startswith("exec"):
            if call.args:
                return ("cmdi-ast.os-system-dynamic",
                        "dynamic program path passed to os.exec*", call.args[0])
            return None
        if attr and base == "os" and attr.startswith("spawn"):
            # os.spawn*(mode, path, ...) - the path is the second argument.
            if len(call.args) >= 2:
                return ("cmdi-ast.os-system-dynamic",
                        "dynamic program path passed to os.spawn*", call.args[1])
            return None
        return None

    # Shell programs whose argv form ``[prog, "-c", <cmd>]`` hands ``<cmd>`` to a
    # shell for interpretation (matched on the basename so ``/bin/bash`` counts).
    _SHELL_PROGRAMS = {"sh", "bash", "dash", "zsh", "ksh"}

    @classmethod
    def _shell_c_command(cls, node: ast.expr):
        """If ``node`` is an argv list/tuple of the form ``["sh", "-c", <cmd>]``
        (any shell program, ``-c`` flag), return the ``<cmd>`` element whose
        constancy decides safety; otherwise ``None``. A constant script stays
        safe; a dynamic one is the injectable shell form even with shell=False."""
        if not isinstance(node, (ast.List, ast.Tuple)):
            return None
        elts = node.elts
        if not elts or not isinstance(elts[0], ast.Constant) \
                or not isinstance(elts[0].value, str):
            return None
        if elts[0].value.rsplit("/", 1)[-1] not in cls._SHELL_PROGRAMS:
            return None
        for i in range(1, len(elts)):
            el = elts[i]
            if isinstance(el, ast.Constant) and el.value == "-c":
                return elts[i + 1] if i + 1 < len(elts) else None
        return None

    @staticmethod
    def _shell_true(call: ast.Call) -> bool:
        """True if the call carries a literal ``shell=True`` keyword."""
        for kw in call.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) \
                    and kw.value.value is True:
                return True
        return False
