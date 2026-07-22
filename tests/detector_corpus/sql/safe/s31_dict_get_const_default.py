# BUG B (safe twin): dict-allowlist .get() whose fallback is a constant. Every
# possible result is an allowlisted identifier, so the ORDER BY is safe.
SORT_COLS = {"name": "name", "price": "price"}


def list_products(conn, sort):
    col = SORT_COLS.get(sort, "name")
    return conn.execute(f"SELECT * FROM products ORDER BY {col}").fetchall()
