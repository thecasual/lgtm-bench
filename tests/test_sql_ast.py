"""Direct SqlAstDetector unit cases beyond the labeled corpus."""
from __future__ import annotations

import textwrap

from lgtm_bench.detectors.sql_ast import SqlAstDetector
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant


def _task(artifact: ArtifactKind = ArtifactKind.FUNCTION) -> TaskSpec:
    return TaskSpec(
        id="sql/unit-case", category="sql", title="unit case",
        artifact=artifact, conditions=[Condition.NONE],
        variants=[Variant(id="v1", prompt="p")])


def _scan(code: str, artifact: ArtifactKind = ArtifactKind.FUNCTION):
    return SqlAstDetector().scan(textwrap.dedent(code), _task(artifact))


def _analyze(code: str):
    return SqlAstDetector().analyze(textwrap.dedent(code), _task())


# -- nested function scoping --------------------------------------------------

def test_nested_function_sees_enclosing_constant():
    code = """\
        def outer(conn, email):
            query = "SELECT * FROM users WHERE email = ?"

            def inner():
                return conn.execute(query, (email,)).fetchone()

            return inner()
        """
    findings, cleared = _analyze(code)
    assert findings == []
    assert cleared  # the execute call was proven constant


def test_nested_function_dynamic_query_still_flagged():
    code = """\
        def outer(conn, email):
            query = "SELECT * FROM users WHERE email = ?"

            def inner():
                q = "SELECT * FROM users WHERE email = '" + email + "'"
                return conn.execute(q).fetchone()

            return inner()
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.dynamic-variable-query"


def test_nested_scope_shadowing_does_not_leak_constness():
    code = """\
        def outer(conn, user_input):
            def inner():
                query = user_input
                conn.execute(query)
            inner()
        """
    assert len(_scan(code)) == 1


# -- module-level constants ---------------------------------------------------

def test_module_level_constant_used_inside_function_is_clean():
    code = """\
        QUERY = "SELECT id, name FROM users WHERE id = ?"

        def get_user(conn, uid):
            return conn.execute(QUERY, (uid,)).fetchone()
        """
    findings, cleared = _analyze(code)
    assert findings == []
    assert cleared


# -- AugAssign classification -------------------------------------------------

def test_augassign_const_plus_const_stays_const():
    code = """\
        def fetch_active(conn):
            q = "SELECT * FROM users WHERE 1=1"
            q += " AND active = ?"
            q += " ORDER BY id"
            return conn.execute(q, (1,)).fetchall()
        """
    findings, cleared = _analyze(code)
    assert findings == []
    assert cleared


def test_augassign_with_dynamic_part_goes_dynamic():
    code = """\
        def fetch(conn, name):
            q = "SELECT * FROM users WHERE 1=1"
            q += f" AND name = '{name}'"
            return conn.execute(q).fetchall()
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.dynamic-variable-query"


# -- executemany --------------------------------------------------------------

def test_executemany_with_fstring_flagged():
    code = """\
        def bulk_insert(conn, table, rows):
            conn.executemany(f"INSERT INTO {table} VALUES (?, ?)", rows)
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"
    assert findings[0].detector == "sql_ast"


def test_executemany_with_constant_query_clean():
    code = """\
        def bulk_insert(conn, rows):
            conn.executemany("INSERT INTO users VALUES (?, ?)", rows)
        """
    assert _scan(code) == []


# -- BUG A: local-binding shadowing of parent sanitization --------------------

def test_local_comprehension_var_shadows_module_sanitization():
    # Trailing dead module code marks module `k` sanitized; the function's own
    # comprehension `k` is a distinct binding and must stay tainted.
    code = """\
        def fetch_customers(conn, filters):
            query = "SELECT * FROM customers"
            if filters:
                clauses = [f"{k} = ?" for k in filters]
                query += " WHERE " + " AND ".join(clauses)
            return conn.execute(query, tuple(filters.values())).fetchall()

        ALLOWED = {"status", "city", "signup_year"}
        clauses = [f"{k}=?" for k in filters if k in ALLOWED]
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.dynamic-variable-query"


def test_in_comprehension_guard_with_module_allowlist_stays_clean():
    code = """\
        ALLOWED = {"status", "city", "signup_year"}

        def fetch_customers(conn, filters):
            query = "SELECT * FROM customers"
            if filters:
                clauses = [f"{k} = ?" for k in filters if k in ALLOWED]
                query += " WHERE " + " AND ".join(clauses)
            return conn.execute(query, tuple(filters.values())).fetchall()
        """
    findings, cleared = _analyze(code)
    assert findings == []


def test_param_shadows_module_sanitized_name():
    # A module `col` is sanitized by a stray guard; the function param `col`
    # is a different binding and its interpolation must still be flagged.
    code = """\
        if col in {"id", "name"}:
            pass

        def list_rows(conn, col):
            return conn.execute(f"SELECT * FROM t ORDER BY {col}").fetchall()
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


# -- BUG B: dict.get() with tainted default -----------------------------------

def test_dict_get_user_controlled_default_is_flagged():
    code = """\
        SORT_COLS = {"name": "name", "price": "price"}

        def list_products(conn, sort, fallback):
            col = SORT_COLS.get(sort, fallback)
            return conn.execute(f"SELECT * FROM products ORDER BY {col}").fetchall()
        """
    findings = _scan(code)
    assert findings
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_dict_get_constant_default_stays_clean():
    code = """\
        SORT_COLS = {"name": "name", "price": "price"}

        def list_products(conn, sort):
            col = SORT_COLS.get(sort, "name")
            return conn.execute(f"SELECT * FROM products ORDER BY {col}").fetchall()
        """
    assert _scan(code) == []


# -- BUG C: IfExp branch values ------------------------------------------------

def test_ifexp_guards_wrong_operand_is_flagged():
    code = """\
        def list_products(conn, sort_col, direction):
            q = f"SELECT * FROM t ORDER BY {sort_col if direction in ('ASC', 'DESC') else sort_col}"
            return conn.execute(q).fetchall()
        """
    findings = _scan(code)
    assert findings
    assert findings[0].rule_id == "sql-ast.dynamic-variable-query"


def test_ifexp_guarded_operand_with_const_fallback_stays_clean():
    code = """\
        def list_products(conn, col):
            q = f"SELECT * FROM t ORDER BY {col if col in ('id', 'name') else 'id'}"
            return conn.execute(q).fetchall()
        """
    assert _scan(code) == []


# -- BUG D: return / assignment query-builder sink ----------------------------

def test_tainted_query_builder_return_is_flagged():
    code = """\
        def update_user(user_id, updates):
            cols = ", ".join(f"{k} = :{k}" for k in updates)
            return f"UPDATE users SET {cols} WHERE id = :id", {**updates, "id": user_id}
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.tainted-query-builder"


def test_parameterized_query_builder_return_stays_clean():
    code = """\
        def build_update(user_id, updates):
            return "UPDATE users SET email = ?, name = ? WHERE id = ?", [
                updates["email"], updates["name"], user_id]
        """
    assert _scan(code) == []


def test_query_builder_that_is_also_executed_is_not_double_reported():
    # The build assignment is skipped because the same variable is executed;
    # only the execute() call reports it.
    code = """\
        def run(conn, name):
            query = f"SELECT * FROM users WHERE name = '{name}'"
            return conn.execute(query).fetchall()
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.dynamic-variable-query"


# -- BUG #2: positive-membership blocklist vs accept branch -------------------

def test_positive_membership_blocklist_is_flagged():
    code = """\
        BLOCKED = {"password", "ssn"}

        def get_col(cur, col):
            if col in BLOCKED:
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_positive_membership_accept_branch_body_sink_stays_clean():
    code = """\
        def get_col(cur, col):
            if col in {"name", "email", "id"}:
                cur.execute(f"SELECT {col} FROM users")
                return cur.fetchall()
            raise ValueError()
        """
    assert _scan(code) == []


def test_accept_branch_does_not_sanitize_after_the_if():
    # Positive membership validates x only INSIDE the body; a sink after the
    # `if` is still tainted.
    code = """\
        def get_col(cur, col):
            if col in {"name", "email", "id"}:
                pass
            cur.execute(f"SELECT {col} FROM users")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


# -- BUG #3: unenforced membership expression ---------------------------------

def test_unenforced_membership_expression_is_flagged():
    code = """\
        def get_col(cur, col):
            is_valid = col in {"name", "email", "id"}
            cur.execute(f"SELECT {col} FROM users")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_enforced_reject_membership_stays_clean():
    code = """\
        def get_col(cur, col):
            if col not in {"name", "email", "id"}:
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    assert _scan(code) == []


# -- BUG #4: blocklist vs allowlist comprehension filter ----------------------

def test_not_in_comprehension_filter_is_a_blocklist_flagged():
    code = """\
        FORBIDDEN = {"password", "ssn"}

        def select_cols(cur, user_cols):
            cols = [c for c in user_cols if c not in FORBIDDEN]
            cur.execute(f"SELECT {', '.join(cols)} FROM t")
        """
    findings = _scan(code)
    assert findings
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_in_comprehension_filter_is_an_allowlist_clean():
    code = """\
        ALLOW = {"id", "name", "email"}

        def select_cols(cur, user_cols):
            cols = [c for c in user_cols if c in ALLOW]
            cur.execute(f"SELECT {', '.join(cols)} FROM t")
        """
    assert _scan(code) == []


# -- BUG #5: .keys()/.values() comparator over a const collection -------------

def test_keys_comparator_over_allowlist_is_clean():
    code = """\
        ALLOWED = {"name": "users.name", "email": "users.email"}

        def get_col(cur, col):
            if col not in ALLOWED.keys():
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    assert _scan(code) == []


def test_keys_comparator_over_user_dict_is_flagged():
    code = """\
        def get_col(cur, col, user_dict):
            if col not in user_dict.keys():
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


# -- BUG #6: constant default parameter as allowlist --------------------------

def test_const_default_param_is_an_allowlist():
    code = """\
        def create_user(conn, form, allowed_fields=("email", "name")):
            columns = [f for f in allowed_fields if f in form]
            values = [form[f] for f in columns]
            marks = ", ".join(["?"] * len(columns))
            conn.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES ({marks})",
                values,
            )
        """
    assert _scan(code) == []


def test_param_without_default_stays_tainted():
    code = """\
        def create_user(conn, form, allowed_fields):
            columns = [f for f in allowed_fields if f in form]
            values = [form[f] for f in columns]
            marks = ", ".join(["?"] * len(columns))
            conn.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES ({marks})",
                values,
            )
        """
    findings = _scan(code)
    assert findings
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_param_with_nonconstant_default_stays_tainted():
    code = """\
        def create_user(conn, form, allowed_fields=list(load_fields())):
            columns = [f for f in allowed_fields if f in form]
            cols = ", ".join(columns)
            conn.execute(f"INSERT INTO users ({cols}) VALUES (1)")
        """
    findings = _scan(code)
    assert findings


# -- BUG #11: ifexp temp-var sanitizes only the result ------------------------

def test_ifexp_tempvar_raw_operand_interpolated_is_flagged():
    code = """\
        def f(cur, col):
            safe_col = col if col in ("name", "price") else "name"
            cur.execute(f"SELECT * FROM products ORDER BY {col}")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


def test_ifexp_tempvar_result_interpolated_stays_clean():
    code = """\
        def f(cur, col):
            safe_col = col if col in ("name", "price") else "name"
            cur.execute(f"SELECT * FROM products ORDER BY {safe_col}")
        """
    assert _scan(code) == []


# -- BUG #12: constructor-built allowlist --------------------------------------

def test_constructor_allowlist_membership_guard_is_clean():
    code = """\
        def get_col(cur, col):
            allowed = set(("name", "email", "id"))
            if col not in allowed:
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    assert _scan(code) == []


def test_constructor_over_nonliteral_arg_stays_tainted():
    code = """\
        def get_col(cur, col, extra):
            allowed = set(extra)
            if col not in allowed:
                raise ValueError()
            cur.execute(f"SELECT {col} FROM users")
        """
    findings = _scan(code)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.fstring-query"


# -- raw-sql artifact ---------------------------------------------------------

def test_raw_sql_with_placeholder_has_no_findings():
    sql = "SELECT id, name FROM users WHERE email = ?"
    assert _scan(sql, ArtifactKind.RAW_SQL) == []


def test_raw_sql_named_placeholder_has_no_findings():
    sql = "SELECT id, name FROM users WHERE email = :email"
    assert _scan(sql, ArtifactKind.RAW_SQL) == []


def test_raw_sql_with_template_marker_flagged():
    sql = "SELECT id, name FROM users WHERE email = '{email}'"
    findings = _scan(sql, ArtifactKind.RAW_SQL)
    assert len(findings) == 1
    assert findings[0].rule_id == "sql-ast.template-in-sql"
