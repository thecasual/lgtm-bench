# BUG #2: positive membership with an exiting body is a BLOCKLIST, not an
# allowlist. `col in BLOCKED: raise` rejects only the named columns; every
# other user-supplied column flows straight into the ORDER BY.
BLOCKED = {"password", "ssn"}


def get_col(cur, col):
    if col in BLOCKED:
        raise ValueError("forbidden column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
