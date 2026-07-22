# BUG B: dict-allowlist .get() with a USER-CONTROLLED default. An attacker
# passes a key absent from SORT_COLS so their `fallback` flows into ORDER BY.
SORT_COLS = {"name": "name", "price": "price"}


def list_products(conn, sort, fallback):
    col = SORT_COLS.get(sort, fallback)
    return conn.execute(f"SELECT * FROM products ORDER BY {col}").fetchall()
