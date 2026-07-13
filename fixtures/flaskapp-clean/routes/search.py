"""Product search and listing helpers."""

SORT_COLS = {"name": "name", "price": "price", "created": "created_at"}


def search_products(conn, name_query):
    """Return products whose name matches the given search text."""
    pattern = "%" + name_query + "%"
    return conn.execute(
        "SELECT id, name, price, created_at FROM products WHERE name LIKE ?",
        (pattern,),
    ).fetchall()


def list_products_sorted(conn, sort):
    """Return all products ordered by the given sort key."""
    column = SORT_COLS[sort] if sort in SORT_COLS else "name"
    query = "SELECT id, name, price, created_at FROM products ORDER BY " + column
    return conn.execute(query).fetchall()
