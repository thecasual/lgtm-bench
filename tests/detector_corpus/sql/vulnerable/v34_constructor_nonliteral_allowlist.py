# BUG #12 (vulnerable twin): `set(extra)` wraps a NON-constant argument, so it
# is not a constant allowlist and the membership guard validates nothing.
def get_col(cur, col, extra):
    allowed = set(extra)
    if col not in allowed:
        raise ValueError("bad column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
