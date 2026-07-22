def list_rows(conn, user_cols, col):
    # An ALLCAPS name is NOT a constant just because it is uppercase — here it
    # is bound to caller-supplied data, so the guard validates nothing.
    COLS = user_cols
    if col not in COLS:
        raise ValueError("bad column")
    return conn.execute(f"SELECT {col} FROM products").fetchall()
