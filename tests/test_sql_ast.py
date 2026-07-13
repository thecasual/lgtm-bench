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
