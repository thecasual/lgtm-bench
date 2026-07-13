# BUG #3 (safe twin): the same allowlist as v29, but here the membership test
# actually gates flow via a reject branch, so the column is validated.
def get_col(cur, col):
    if col not in {"name", "email", "id"}:
        raise ValueError("unsupported column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
