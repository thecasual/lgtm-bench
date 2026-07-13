# BUG #2 (safe twin): a POSITIVE membership test whose body does NOT exit is a
# genuine accept branch — the sink lives inside the `if`, so the column is
# validated for exactly the code that uses it.
def get_col(cur, col):
    if col in {"name", "email", "id"}:
        cur.execute(f"SELECT {col} FROM users")
        return cur.fetchall()
    raise ValueError("unsupported column")
